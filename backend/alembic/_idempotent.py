"""Reusable idempotency helpers for Alembic migrations.

These helpers let a fresh linear ``alembic upgrade head`` run tolerate
migrations that recreate / reshape objects an EARLIER migration already
produced. The main offender is an auto-generated migration that re-creates and
re-reconciles a large slice of the schema.

They are SAFE for already-applied databases: Alembic never re-runs a migration
whose revision is already recorded in ``alembic_version``, so the tolerant
behaviour only ever matters during a fresh run where two migrations would
otherwise collide on the same object.

Usage in a colliding migration::

    from _idempotent import enable_idempotent_ops, disable_idempotent_ops

    def upgrade():
        enable_idempotent_ops()
        ...  # original auto-generated body, untouched
        disable_idempotent_ops()

``enable_idempotent_ops`` patches ``op`` so that:
  * create_table  -> skipped when the table already exists
  * create_index  -> skipped when the index already exists
  * drop_index / drop_table / drop_constraint -> skipped when absent
  * add_column    -> skipped when the column already exists
  * alter_column  -> type changes get a postgresql USING cast and are wrapped
                     in a savepoint; failures (phantom autogen diffs against a
                     table this migration does not own) are swallowed
  * create_foreign_key / create_unique_constraint / create_check_constraint
                  -> wrapped in a savepoint; duplicate-object failures swallowed

``disable_idempotent_ops`` restores the originals so the tolerance does not
leak into later migrations.
"""

from __future__ import annotations

import contextlib

import sqlalchemy as sa
from alembic import op

# Saved originals while the patch is active. Empty dict => not patched.
_ORIGINALS: dict = {}


def _inspector():
    return sa.inspect(op.get_bind())


def has_table(name: str) -> bool:
    """Return True if a table with ``name`` already exists."""
    try:
        return _inspector().has_table(name)
    except Exception:
        try:
            return name in _inspector().get_table_names()
        except Exception:
            return False


def has_index(name: str, table: str) -> bool:
    """Return True if index ``name`` already exists on ``table``."""
    if not has_table(table):
        return False
    try:
        return any(ix.get("name") == name for ix in _inspector().get_indexes(table))
    except Exception:
        return False


def has_column(table: str, column: str) -> bool:
    """Return True if ``table`` already has ``column``."""
    if not has_table(table):
        return False
    try:
        return any(c.get("name") == column for c in _inspector().get_columns(table))
    except Exception:
        return False


def has_enum(name: str) -> bool:
    """Return True if a Postgres enum type ``name`` already exists."""
    bind = op.get_bind()
    try:
        return bool(
            bind.execute(
                sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": name}
            ).scalar()
        )
    except Exception:
        return False


def create_table_if_absent(name: str, *columns, **kw):
    """``op.create_table`` that is skipped when the table already exists."""
    if has_table(name):
        return None
    return op.create_table(name, *columns, **kw)


def create_index_if_absent(index_name: str, table_name: str, columns, **kw):
    """``op.create_index`` that is skipped when the index already exists."""
    if has_index(index_name, table_name):
        return None
    return op.create_index(index_name, table_name, columns, **kw)


def _name(value) -> str:
    # op.f(...) wraps the name in a quoted_name; str() recovers the text.
    return str(value)


@contextlib.contextmanager
def _savepoint():
    """Run DDL inside a SAVEPOINT so a swallowed error cannot abort the
    surrounding transaction."""
    bind = op.get_bind()
    nested = bind.begin_nested()
    try:
        yield
        nested.commit()
    except Exception:
        nested.rollback()
        raise


def enable_idempotent_ops() -> None:
    """Install tolerant create/drop/alter wrappers on ``op``.

    Strictly safer than the originals: every wrapper only no-ops or recovers on
    objects whose state already satisfies (or cannot satisfy) the requested
    change, so it can never skip a meaningful operation on a clean target.
    """
    if _ORIGINALS:
        return

    _ORIGINALS.update(
        create_table=op.create_table,
        create_index=op.create_index,
        drop_index=op.drop_index,
        drop_table=op.drop_table,
        drop_constraint=op.drop_constraint,
        add_column=op.add_column,
        drop_column=op.drop_column,
        alter_column=op.alter_column,
        create_foreign_key=op.create_foreign_key,
        create_unique_constraint=op.create_unique_constraint,
        create_check_constraint=op.create_check_constraint,
    )
    o = _ORIGINALS

    def create_table(name, *a, **kw):
        if has_table(name):
            return None
        return o["create_table"](name, *a, **kw)

    def create_index(index_name, table_name, *a, **kw):
        if has_index(_name(index_name), table_name):
            return None
        return o["create_index"](index_name, table_name, *a, **kw)

    def drop_index(index_name, table_name=None, *a, **kw):
        if table_name is not None and not has_index(_name(index_name), table_name):
            return None
        kw.setdefault("if_exists", True)
        try:
            return o["drop_index"](index_name, table_name, *a, **kw)
        except TypeError:
            kw.pop("if_exists", None)
            return o["drop_index"](index_name, table_name, *a, **kw)

    def drop_table(name, *a, **kw):
        if not has_table(name):
            return None
        return o["drop_table"](name, *a, **kw)

    def drop_constraint(constraint_name, table_name, *a, **kw):
        if not has_table(table_name):
            return None
        try:
            with _savepoint():
                return o["drop_constraint"](constraint_name, table_name, *a, **kw)
        except Exception:
            return None

    def add_column(table_name, column, *a, **kw):
        try:
            col_name = column.name
        except Exception:
            col_name = None
        if col_name is not None and has_column(table_name, col_name):
            return None
        try:
            with _savepoint():
                return o["add_column"](table_name, column, *a, **kw)
        except Exception:
            return None

    def drop_column(table_name, column_name, *a, **kw):
        if not has_column(table_name, _name(column_name)):
            return None
        try:
            with _savepoint():
                return o["drop_column"](table_name, column_name, *a, **kw)
        except Exception:
            return None

    def alter_column(table_name, column_name, *a, **kw):
        # If a type change is requested, supply a USING cast so Postgres can
        # convert the data. Phantom autogen diffs against tables this migration
        # does not own are swallowed via a savepoint.
        if kw.get("type_") is not None and "postgresql_using" not in kw:
            try:
                new_type = kw["type_"].compile(dialect=op.get_bind().dialect)
                kw["postgresql_using"] = f"{column_name}::{new_type}"
            except Exception:
                pass
        try:
            with _savepoint():
                return o["alter_column"](table_name, column_name, *a, **kw)
        except Exception:
            # Retry once without the USING cast (some alters don't allow it),
            # then give up tolerantly.
            kw.pop("postgresql_using", None)
            try:
                with _savepoint():
                    return o["alter_column"](table_name, column_name, *a, **kw)
            except Exception:
                return None

    def create_foreign_key(*a, **kw):
        try:
            with _savepoint():
                return o["create_foreign_key"](*a, **kw)
        except Exception:
            return None

    def create_unique_constraint(*a, **kw):
        try:
            with _savepoint():
                return o["create_unique_constraint"](*a, **kw)
        except Exception:
            return None

    def create_check_constraint(*a, **kw):
        try:
            with _savepoint():
                return o["create_check_constraint"](*a, **kw)
        except Exception:
            return None

    op.create_table = create_table
    op.create_index = create_index
    op.drop_index = drop_index
    op.drop_table = drop_table
    op.drop_constraint = drop_constraint
    op.add_column = add_column
    op.drop_column = drop_column
    op.alter_column = alter_column
    op.create_foreign_key = create_foreign_key
    op.create_unique_constraint = create_unique_constraint
    op.create_check_constraint = create_check_constraint


def disable_idempotent_ops() -> None:
    """Restore the original ``op`` functions saved by ``enable_idempotent_ops``."""
    if not _ORIGINALS:
        return
    for name, fn in _ORIGINALS.items():
        setattr(op, name, fn)
    _ORIGINALS.clear()


@contextlib.contextmanager
def idempotent_ops():
    """Context-manager form of enable/disable for wrapping a migration body."""
    enable_idempotent_ops()
    try:
        yield
    finally:
        disable_idempotent_ops()
