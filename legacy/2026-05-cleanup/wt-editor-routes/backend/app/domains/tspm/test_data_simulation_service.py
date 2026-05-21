"""Schema parsing and simulation helpers for TSPM test data flows."""

from __future__ import annotations

import os
import random
import re
import string
from typing import Any

from fastapi import HTTPException


def parse_schema_from_ddl(body: dict) -> dict:
    ddl = (body.get("ddl") or "").strip()
    if not ddl:
        raise HTTPException(400, "ddl alanı gerekli")
    from app.domains.tspm.db_schema_parser import parse_ddl

    return parse_ddl(ddl)


def parse_schema_from_csv(body: dict) -> dict:
    csv_text = (body.get("csv_text") or "").strip()
    if not csv_text:
        raise HTTPException(400, "csv_text alanı gerekli")
    table_name = body.get("table_name", "imported_table")
    has_header = bool(body.get("has_header", True))
    from app.domains.tspm.db_schema_parser import parse_csv

    return parse_csv(csv_text, table_name, has_header)


def parse_schema_from_natural_language(body: dict) -> dict:
    description = (body.get("description") or "").strip()
    if len(description) < 10:
        raise HTTPException(400, "description en az 10 karakter olmalı")
    try:
        from app.domains.tspm.db_schema_parser import parse_natural_language

        return parse_natural_language(description)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


def parse_schema_from_db(body: dict) -> dict:
    conn_str = (body.get("connection_string") or "").strip()
    if not conn_str:
        raise HTTPException(400, "connection_string alanı gerekli")

    _validate_supported_connection(conn_str, "Yalnızca PostgreSQL ve SQLite bağlantı stringleri desteklenir.")
    conn_str = _rewrite_localhost_for_docker(conn_str)

    schema_name = body.get("schema_name", "public")
    exclude_tables = body.get("exclude_tables") or []

    from app.domains.tspm.db_schema_parser import parse_db_connection

    try:
        return parse_db_connection(conn_str, schema_name, exclude_tables)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


def standalone_simulate(body: dict) -> dict:
    tables_def = body.get("tables") or []
    if not tables_def:
        raise HTTPException(400, "tables dizisi gerekli")
    return _simulate_tables(
        tables_def=tables_def,
        locale=body.get("locale", "tr_TR"),
        quality_check=bool(body.get("quality_check", True)),
        seed=42,
    )


def write_simulated_to_db(body: dict) -> dict:
    conn_str = (body.get("connection_string") or "").strip()
    if not conn_str:
        raise HTTPException(400, "connection_string gerekli")
    _validate_supported_connection(conn_str, "Yalnızca PostgreSQL ve SQLite desteklenir.")

    tables_data: dict = body.get("tables") or {}
    if not tables_data:
        raise HTTPException(400, "tables verisi gerekli")

    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise HTTPException(500, "sqlalchemy paketi yüklü değil.") from exc

    try:
        engine = create_engine(
            conn_str,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
    except Exception as exc:
        raise HTTPException(422, f"Bağlantı oluşturulamadı: {exc}") from exc

    safe_identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")

    def _validate_identifier(name: str, kind: str) -> None:
        if not safe_identifier.match(name):
            raise HTTPException(
                400,
                f"Güvensiz {kind} adı: '{name}'. Yalnızca harf, rakam ve alt çizgi kullanılabilir.",
            )

    for table_name, table_data in tables_data.items():
        _validate_identifier(table_name, "tablo")
        for column in table_data.get("columns", []):
            _validate_identifier(column, "kolon")

    written: dict[str, int] = {}
    errors: list[str] = []
    try:
        with engine.begin() as conn:
            for table_name, table_data in tables_data.items():
                columns: list[str] = table_data.get("columns", [])
                rows: list = table_data.get("rows", [])
                if not columns or not rows:
                    written[table_name] = 0
                    continue

                col_list = ", ".join(f'"{column}"' for column in columns)
                placeholders = ", ".join(f":{column}" for column in columns)
                stmt = text(f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})')
                params = [dict(zip(columns, row)) for row in rows]
                try:
                    conn.execute(stmt, params)
                    written[table_name] = len(rows)
                except Exception as exc:
                    errors.append(f"{table_name}: {exc}")
    except Exception as exc:
        raise HTTPException(422, f"Yazma hatası: {exc}") from exc
    finally:
        engine.dispose()

    return {
        "written": written,
        "total_rows": sum(written.values()),
        "errors": errors,
        "success": len(errors) == 0,
    }


def ai_enrich_schema(body: dict) -> dict:
    tables = body.get("tables") or []
    if not tables:
        raise HTTPException(400, "tables dizisi gerekli")
    from app.domains.tspm.db_schema_parser import enrich_schema

    return enrich_schema(tables, body.get("domain_hint", ""))


def full_simulate(body: dict) -> dict:
    tables_def = body.get("tables") or []
    if not tables_def:
        raise HTTPException(400, "tables dizisi gerekli")
    return _simulate_tables(
        tables_def=tables_def,
        locale=body.get("locale", "tr_TR"),
        quality_check=bool(body.get("quality_check", True)),
        seed=42,
    )


def simulate_schema_for_project(body: dict) -> dict:
    tables_def = body.get("tables") or []
    if not tables_def:
        raise HTTPException(400, "tables dizisi gerekli")
    return _simulate_tables(
        tables_def=tables_def,
        locale=body.get("locale", "tr_TR"),
        quality_check=False,
        seed=0,
    )


def _simulate_tables(
    *,
    tables_def: list,
    locale: str,
    quality_check: bool,
    seed: int,
) -> dict:
    Faker = _require_faker()
    fake = Faker(locale)
    Faker.seed(seed)
    faker_map = _make_faker_map(fake)
    generated_tables: dict = {}
    sim_result: dict = {}

    for table in tables_def:
        table_name = table.get("name", f"tablo_{len(sim_result)}")
        row_count = min(int(table.get("rowCount", table.get("row_count", 10))), 2000)
        cols_def = table.get("columns", [])
        if not cols_def:
            continue

        unique_sets: dict[str, set] = {}
        counter: dict[str, int] = {}
        columns = [column["name"] for column in cols_def]
        col_data: dict[str, list] = {column: [] for column in columns}

        for row_idx in range(row_count):
            for column in cols_def:
                col_name = column["name"]
                col_type = column.get("type", "word")
                unique = column.get("unique", False)
                if unique and col_name not in unique_sets:
                    unique_sets[col_name] = set()

                for _ in range(20):
                    value = _generate_value(
                        column,
                        col_type,
                        col_name,
                        faker_map,
                        fake,
                        counter,
                        generated_tables,
                        row_idx,
                    )
                    if not unique or value not in unique_sets.get(col_name, set()):
                        break
                else:
                    value = f"{value}_{row_idx}"

                if unique:
                    unique_sets[col_name].add(value)
                col_data[col_name].append(value)

        generated_tables[table_name] = col_data
        rows = [[col_data[column][i] for column in columns] for i in range(row_count)]
        sim_result[table_name] = {"columns": columns, "rows": rows, "row_count": row_count}

    result: dict = {"tables": sim_result, "table_count": len(sim_result)}
    if quality_check:
        from app.domains.tspm.db_schema_parser import run_quality_check

        result.update(run_quality_check(result, tables_def))
    return result


def _make_faker_map(fake) -> dict[str, Any]:
    return {
        "name": fake.name,
        "first_name": fake.first_name,
        "last_name": fake.last_name,
        "email": fake.email,
        "phone": fake.phone_number,
        "address": fake.address,
        "city": fake.city,
        "company": fake.company,
        "text": fake.text,
        "sentence": fake.sentence,
        "word": fake.word,
        "uuid": fake.uuid4,
        "date": lambda: fake.date().isoformat(),
        "datetime": lambda: fake.date_time().isoformat(),
        "iban": fake.iban if hasattr(fake, "iban") else lambda: fake.numerify("TR####################"),
        "tc_kimlik": lambda: fake.numerify("###########"),
        "url": fake.url,
        "ipv4": fake.ipv4,
        "username": fake.user_name,
        "password": lambda: fake.password(length=12),
        "color": fake.color_name,
        "job": fake.job,
    }


def _generate_value(
    col: dict,
    col_type: str,
    col_name: str,
    faker_map: dict,
    fake,
    counter: dict,
    generated_tables: dict,
    row_idx: int,
) -> str:
    if col_type == "auto_increment":
        counter[col_name] = counter.get(col_name, 0) + 1
        return str(counter[col_name])

    if col_type == "foreign_key":
        ref: str = col.get("references", "")
        if "." in ref:
            ref_table, ref_col = ref.rsplit(".", 1)
            pool = generated_tables.get(ref_table, {}).get(ref_col, [])
            if pool:
                return random.choice(pool)
        return str(row_idx + 1)

    if col_type == "enum":
        return str(random.choice(col.get("values", ["a", "b", "c"])))

    if col_type == "boolean":
        weights = col.get("weights", [50, 50])
        return str(random.choices(["true", "false"], weights=weights)[0])

    if col_type == "integer":
        return str(random.randint(int(col.get("min", 0)), int(col.get("max", 9999))))

    if col_type == "decimal":
        value = random.uniform(float(col.get("min", 0)), float(col.get("max", 9999)))
        return f"{value:.{int(col.get('precision', 2))}f}"

    if col_type == "regex":
        pattern: str = col.get("pattern", "[A-Z]{3}")
        try:
            return _expand_simple_regex(pattern)
        except Exception:
            return fake.bothify(pattern.replace("[A-Z]", "?").replace("[0-9]", "#"))

    if col_type == "string":
        min_len = int(col.get("min_length", 5))
        max_len = int(col.get("max_length", 20))
        length = random.randint(min_len, max_len)
        return "".join(random.choices(string.ascii_letters, k=length))

    if col_type == "sequence":
        prefix = col.get("prefix", "")
        start = int(col.get("start", 1))
        counter[col_name] = counter.get(col_name, start - 1) + 1
        return f"{prefix}{counter[col_name]}"

    fn = faker_map.get(col_type)
    if fn:
        return str(fn())
    return str(fake.word())


def _expand_simple_regex(pattern: str) -> str:
    result_chars = []
    i = 0
    while i < len(pattern):
        if pattern[i] == "[":
            end = pattern.index("]", i)
            charset = pattern[i + 1 : end]
            repeat = 1
            if end + 1 < len(pattern) and pattern[end + 1] == "{":
                end2 = pattern.index("}", end + 1)
                repeat = int(pattern[end + 2 : end2])
                i = end2 + 1
            else:
                i = end + 1
            pool_chars = []
            j = 0
            while j < len(charset):
                if j + 2 < len(charset) and charset[j + 1] == "-":
                    pool_chars += [chr(c) for c in range(ord(charset[j]), ord(charset[j + 2]) + 1)]
                    j += 3
                else:
                    pool_chars.append(charset[j])
                    j += 1
            result_chars.append("".join(random.choice(pool_chars) for _ in range(repeat)))
        elif pattern[i] == "\\" and i + 1 < len(pattern):
            result_chars.append(pattern[i + 1])
            i += 2
        else:
            result_chars.append(pattern[i])
            i += 1
    return "".join(result_chars)


def _validate_supported_connection(conn_str: str, message: str) -> None:
    allowed = ("postgresql://", "postgresql+psycopg2://", "sqlite:///")
    if not any(conn_str.startswith(prefix) for prefix in allowed):
        raise HTTPException(400, message)


def _rewrite_localhost_for_docker(conn_str: str) -> str:
    if os.environ.get("RUNNING_IN_DOCKER") or os.path.exists("/.dockerenv"):
        return re.sub(
            r"(postgresql(?:\+psycopg2)?://)([^:@/]*)(:([^@/]*))?@(localhost|127\.0\.0\.1)(:\d+)?/",
            lambda match: (
                f"{match.group(1)}{match.group(2)}"
                f"{(':' + match.group(4)) if match.group(4) else ''}"
                f"@postgres{match.group(6) or ':5432'}/"
            ),
            conn_str,
        )
    return conn_str


def _require_faker():
    try:
        from faker import Faker
    except ImportError as exc:
        raise HTTPException(500, "faker paketi yüklü değil.") from exc
    return Faker
