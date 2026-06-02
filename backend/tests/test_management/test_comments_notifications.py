"""Service-level tests for M-50 Threaded Comments + M-45 Notification Inbox.

These tests bypass FastAPI and exercise ``comments_service`` directly
against the real Postgres development database. The router is covered
implicitly via the same exception-→-status mapping (we assert on the
``ValueError`` / ``KeyError`` raised by the service, which the router
maps to 400 / 403 / 404).

Coverage:

* ``TestParseMentions`` - pure helper, no DB.
* ``TestCreateComment`` - happy path, parent reply, validation.
* ``TestListComments`` - ordering, tenant isolation, soft delete tombstones.
* ``TestEditDeleteComment`` - permissions, admin override.
* ``TestReactToComment`` - idempotency, add/remove, empty bucket cleanup.
* ``TestMentionFanout`` - notification fan-out on mentions and replies.
* ``TestNotifications`` - list filtering, mark read/archive/all.
* ``TestSSEStream`` - asyncio stream smoke test.
* ``TestRouterRegistration`` - endpoint surface check (no DB).
"""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone

import pytest


# ── Pure helpers (no DB) ─────────────────────────────────────────────────────


class TestParseMentions:
    def test_returns_empty_for_empty_body(self) -> None:
        from app.domains.test_management.comments_service import parse_mentions

        assert parse_mentions("", None) == []
        assert parse_mentions("", []) == []

    def test_extracts_uuid_from_body(self) -> None:
        from app.domains.test_management.comments_service import parse_mentions

        u = str(uuid.uuid4())
        out = parse_mentions(f"Hi @{u} please review", None)
        assert out == [u]

    def test_dedups_explicit_and_inline(self) -> None:
        from app.domains.test_management.comments_service import parse_mentions

        u1 = str(uuid.uuid4())
        u2 = str(uuid.uuid4())
        out = parse_mentions(f"@{u1} cc @{u2}", [u1, u1, u2])
        # explicit comes first (insertion order), inline matches already-seen are skipped
        assert out == [u1, u2]

    def test_rejects_non_uuid_explicit(self) -> None:
        from app.domains.test_management.comments_service import parse_mentions

        u = str(uuid.uuid4())
        out = parse_mentions("body", ["not-a-uuid", "", u])
        assert out == [u]

    def test_inline_uuids_appended_after_explicit(self) -> None:
        from app.domains.test_management.comments_service import parse_mentions

        u1 = str(uuid.uuid4())
        u2 = str(uuid.uuid4())
        out = parse_mentions(f"foo @{u2}", [u1])
        assert out == [u1, u2]


class TestRouterRegistration:
    def test_comment_and_notification_routes_registered(self) -> None:
        from app.domains.test_management.router import router

        paths = {route.path for route in router.routes}
        for required in (
            "/test-management/comments",
            "/test-management/comments/{comment_id}",
            "/test-management/comments/{comment_id}/react",
            "/test-management/notifications",
            "/test-management/notifications/unread-count",
            "/test-management/notifications/{notification_id}/read",
            "/test-management/notifications/{notification_id}/archive",
            "/test-management/notifications/read-all",
            "/test-management/notifications/stream",
        ):
            assert required in paths, f"Route {required} not registered"


# ── DB-backed service tests ──────────────────────────────────────────────────


@pytest.fixture()
def case_entity() -> dict[str, str]:
    """A synthetic 'case' entity (no DB row needed — comments are polymorphic)."""
    return {"entity_type": "case", "entity_id": str(uuid.uuid4())}


class TestCreateComment:
    def test_happy_path(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        user = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session,
            MgmtCommentCreate(
                entity_type=case_entity["entity_type"],
                entity_id=case_entity["entity_id"],
                body_md="Hello world",
            ),
            user,
        )
        assert c.id is not None
        assert c.body_md == "Hello world"
        assert c.author_id == seeded_users["alice"]
        assert c.parent_id is None
        assert c.mentions == []
        assert c.deleted_at is None

    def test_parent_reply(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        bob = make_user(seeded_users["bob"])
        root = comments_service.create_comment(
            db_session,
            MgmtCommentCreate(**case_entity, body_md="root"),
            alice,
        )
        reply = comments_service.create_comment(
            db_session,
            MgmtCommentCreate(**case_entity, parent_id=root.id, body_md="reply"),
            bob,
        )
        assert reply.parent_id == root.id

    def test_cross_entity_reply_rejected(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        case_id_a = str(uuid.uuid4())
        case_id_b = str(uuid.uuid4())
        root = comments_service.create_comment(
            db_session,
            MgmtCommentCreate(entity_type="case", entity_id=case_id_a, body_md="A"),
            alice,
        )
        with pytest.raises(ValueError, match="Parent comment"):
            comments_service.create_comment(
                db_session,
                MgmtCommentCreate(
                    entity_type="case",
                    entity_id=case_id_b,
                    parent_id=root.id,
                    body_md="cross",
                ),
                alice,
            )

    def test_invalid_entity_type_at_schema(self) -> None:
        from pydantic import ValidationError

        from app.domains.test_management.schemas import MgmtCommentCreate

        with pytest.raises(ValidationError):
            MgmtCommentCreate(entity_type="xxx", entity_id=str(uuid.uuid4()), body_md="x")

    def test_empty_body_rejected(self) -> None:
        from pydantic import ValidationError

        from app.domains.test_management.schemas import MgmtCommentCreate

        with pytest.raises(ValidationError):
            MgmtCommentCreate(entity_type="case", entity_id=str(uuid.uuid4()), body_md="")

    def test_mentions_combined_from_body_and_payload(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        u_bob = seeded_users["bob"]
        u_carol = seeded_users["carol"]
        c = comments_service.create_comment(
            db_session,
            MgmtCommentCreate(
                **case_entity,
                body_md=f"Hey @{u_carol}, ping @{u_bob} again",
                mentions=[u_bob],  # explicit dup with inline
            ),
            alice,
        )
        # explicit first, inline appended without dup
        assert c.mentions[0] == u_bob
        assert u_carol in c.mentions
        assert len(c.mentions) == 2


class TestListComments:
    def test_orders_by_created_at(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        ids = []
        for n in range(3):
            c = comments_service.create_comment(
                db_session,
                MgmtCommentCreate(**case_entity, body_md=f"msg-{n}"),
                alice,
            )
            ids.append(c.id)
        out = comments_service.list_comments(
            db_session,
            entity_type=case_entity["entity_type"],
            entity_id=case_entity["entity_id"],
            tenant_id=seeded_users["_tenants"]["alice"],
        )
        assert [c.id for c in out] == ids

    def test_tenant_isolation(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        tenant_a = seeded_users["_tenants"]["alice"]
        tenant_b = seeded_users["_tenants"]["eve"]
        alice = make_user(seeded_users["alice"], tenant_id=tenant_a)
        eve = make_user(seeded_users["eve"], tenant_id=tenant_b)
        comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="a"), alice
        )
        comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="b"), eve
        )
        out_a = comments_service.list_comments(
            db_session, **case_entity, tenant_id=tenant_a
        )
        out_b = comments_service.list_comments(
            db_session, **case_entity, tenant_id=tenant_b
        )
        assert all(c.tenant_id == tenant_a for c in out_a)
        assert all(c.tenant_id == tenant_b for c in out_b)
        assert {c.body_md for c in out_a} == {"a"}
        assert {c.body_md for c in out_b} == {"b"}

    def test_soft_deleted_excluded_by_default_included_with_flag(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="bye"), alice
        )
        comments_service.delete_comment(db_session, c.id, alice)
        tenant_a = seeded_users["_tenants"]["alice"]
        default = comments_service.list_comments(
            db_session, **case_entity, tenant_id=tenant_a
        )
        with_deleted = comments_service.list_comments(
            db_session, **case_entity, tenant_id=tenant_a, include_deleted=True
        )
        assert all(x.id != c.id for x in default)
        assert any(x.id == c.id for x in with_deleted)


class TestEditDeleteComment:
    def test_author_can_edit(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate, MgmtCommentUpdate

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="orig"), alice
        )
        edited = comments_service.update_comment(
            db_session, c.id, MgmtCommentUpdate(body_md="new"), alice
        )
        assert edited.body_md == "new"
        assert edited.edited_at is not None

    def test_non_author_edit_rejected(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate, MgmtCommentUpdate

        alice = make_user(seeded_users["alice"])
        bob = make_user(seeded_users["bob"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="orig"), alice
        )
        with pytest.raises(ValueError, match="yazar"):
            comments_service.update_comment(
                db_session, c.id, MgmtCommentUpdate(body_md="hack"), bob
            )

    def test_admin_override_delete(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        admin = make_user(seeded_users["admin"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="orig"), alice
        )
        deleted = comments_service.delete_comment(db_session, c.id, admin, is_admin=True)
        assert deleted.deleted_at is not None

    def test_non_author_non_admin_delete_rejected(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        bob = make_user(seeded_users["bob"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="orig"), alice
        )
        with pytest.raises(ValueError):
            comments_service.delete_comment(db_session, c.id, bob, is_admin=False)

    def test_soft_delete_renders_empty_body_in_serializer(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.comments_service import _serialize_comment
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="secret"), alice
        )
        comments_service.delete_comment(db_session, c.id, alice)
        db_session.expire_all()
        c2 = comments_service.get_comment(db_session, c.id)
        out = _serialize_comment(c2)
        assert out["body_md"] == ""
        assert out["deleted_at"] is not None
        assert out["id"] == c.id

    def test_react_on_deleted_blocked(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate, MgmtCommentReact

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="x"), alice
        )
        comments_service.delete_comment(db_session, c.id, alice)
        with pytest.raises(ValueError):
            comments_service.react_to_comment(
                db_session, c.id, MgmtCommentReact(emoji="+1"), alice
            )


class TestReactToComment:
    def test_add_then_remove(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate, MgmtCommentReact

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="x"), alice
        )
        c2 = comments_service.react_to_comment(
            db_session, c.id, MgmtCommentReact(emoji="+1", add=True), alice
        )
        assert seeded_users["alice"] in c2.reactions["+1"]
        c3 = comments_service.react_to_comment(
            db_session, c.id, MgmtCommentReact(emoji="+1", add=False), alice
        )
        assert "+1" not in c3.reactions

    def test_idempotent_add(self, db_session, seeded_users, make_user, case_entity) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate, MgmtCommentReact

        alice = make_user(seeded_users["alice"])
        c = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="x"), alice
        )
        for _ in range(3):
            c = comments_service.react_to_comment(
                db_session, c.id, MgmtCommentReact(emoji="heart", add=True), alice
            )
        assert c.reactions["heart"].count(seeded_users["alice"]) == 1


class TestMentionFanout:
    def _list_user_notifs(self, db, user_id):
        from app.domains.test_management import comments_service
        return comments_service.list_notifications(db, user_id=user_id, limit=100)

    def test_mention_creates_notification(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        u_bob = seeded_users["bob"]
        comments_service.create_comment(
            db_session,
            MgmtCommentCreate(**case_entity, body_md=f"@{u_bob} fyi"),
            alice,
        )
        bob_notifs = self._list_user_notifs(db_session, u_bob)
        kinds = [n.kind for n in bob_notifs]
        assert "mention" in kinds

    def test_self_mention_skipped(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        u_alice = seeded_users["alice"]
        before = len(self._list_user_notifs(db_session, u_alice))
        comments_service.create_comment(
            db_session,
            MgmtCommentCreate(**case_entity, body_md=f"@{u_alice} self"),
            alice,
        )
        after = len(self._list_user_notifs(db_session, u_alice))
        assert after == before  # no self-notification

    def test_reply_notifies_parent_author(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        bob = make_user(seeded_users["bob"])
        root = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="root"), alice
        )
        comments_service.create_comment(
            db_session,
            MgmtCommentCreate(**case_entity, parent_id=root.id, body_md="reply"),
            bob,
        )
        alice_notifs = self._list_user_notifs(db_session, seeded_users["alice"])
        assert any(n.kind == "comment_reply" for n in alice_notifs)

    def test_reply_notification_not_duplicated_if_parent_author_in_mentions(
        self, db_session, seeded_users, make_user, case_entity
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        bob = make_user(seeded_users["bob"])
        u_alice = seeded_users["alice"]
        root = comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="root"), alice
        )
        before = len(self._list_user_notifs(db_session, u_alice))
        comments_service.create_comment(
            db_session,
            MgmtCommentCreate(
                **case_entity,
                parent_id=root.id,
                body_md=f"@{u_alice} pong",
            ),
            bob,
        )
        after_notifs = self._list_user_notifs(db_session, u_alice)
        new = len(after_notifs) - before
        # Exactly one notification (the mention) — reply must not be duplicated
        assert new == 1
        assert after_notifs[0].kind == "mention"


class TestNotifications:
    def test_create_and_list(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        bob = seeded_users["bob"]
        comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(
                user_id=bob, kind="system", title="Welcome", body="hi"
            ),
            admin,
        )
        out = comments_service.list_notifications(db_session, user_id=bob)
        assert any(n.title == "Welcome" for n in out)

    def test_unread_only_filter(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        bob = seeded_users["bob"]
        n1 = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(user_id=bob, kind="system", title="A"),
            admin,
        )
        n2 = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(user_id=bob, kind="system", title="B"),
            admin,
        )
        comments_service.mark_read(db_session, notification_id=n1.id, user_id=bob)
        unread = comments_service.list_notifications(
            db_session, user_id=bob, unread_only=True
        )
        ids = {n.id for n in unread}
        assert n2.id in ids
        assert n1.id not in ids

    def test_mark_archived_sets_read_if_unread(
        self, db_session, seeded_users, make_user
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        bob = seeded_users["bob"]
        n = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(user_id=bob, kind="system", title="A"),
            admin,
        )
        archived = comments_service.mark_archived(
            db_session, notification_id=n.id, user_id=bob
        )
        assert archived.archived_at is not None
        assert archived.read_at is not None

    def test_mark_all_read(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        bob = seeded_users["bob"]
        for i in range(3):
            comments_service.create_notification(
                db_session,
                MgmtNotificationCreate(user_id=bob, kind="system", title=f"N{i}"),
                admin,
            )
        affected = comments_service.mark_all_read(db_session, user_id=bob)
        assert affected >= 3
        unread = comments_service.list_notifications(
            db_session, user_id=bob, unread_only=True
        )
        assert unread == []

    def test_unread_count(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        bob = seeded_users["bob"]
        before_unread, before_total = comments_service.count_notifications(
            db_session, user_id=bob
        )
        comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(user_id=bob, kind="system", title="X"),
            admin,
        )
        unread, total = comments_service.count_notifications(db_session, user_id=bob)
        assert unread == before_unread + 1
        assert total == before_total + 1

    def test_mark_read_wrong_user_404(self, db_session, seeded_users, make_user) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        n = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(user_id=seeded_users["bob"], kind="system", title="A"),
            admin,
        )
        with pytest.raises(KeyError):
            comments_service.mark_read(
                db_session, notification_id=n.id, user_id=seeded_users["alice"]
            )

    def test_unknown_kind_coerced_to_system(
        self, db_session, seeded_users, make_user
    ) -> None:
        # Direct internal helper test for the soft-allow behaviour.
        from app.domains.test_management.comments_service import _create_notification

        n = _create_notification(
            db_session,
            user_id=seeded_users["bob"],
            kind="some_random_kind",
            title="t",
            body="b",
            link_path=None,
            severity="info",
            project_id=None,
            tenant_id="00000000-0000-0000-0000-000000000001",
        )
        db_session.commit()
        assert n.kind == "system"


# ── SSE smoke test ───────────────────────────────────────────────────────────


class TestSSEStream:
    def test_stream_yields_connected_then_keepalive(self) -> None:
        from app.domains.test_management.comments_service import stream_events

        async def consume() -> list[bytes]:
            collected: list[bytes] = []
            agen = stream_events("user-x", keepalive_seconds=0.05)
            try:
                # First chunk is the immediate "connected" hello.
                collected.append(await asyncio.wait_for(agen.__anext__(), timeout=1.0))
                # Second chunk must be the keepalive (after timeout).
                collected.append(await asyncio.wait_for(agen.__anext__(), timeout=1.0))
            finally:
                await agen.aclose()
            return collected

        chunks = asyncio.run(consume())
        assert chunks[0] == b": connected\n\n"
        assert chunks[1] == b": keepalive\n\n"

    def test_publish_routes_to_subscriber(self) -> None:
        from app.domains.test_management.comments_service import _bus

        async def scenario() -> dict:
            q = await _bus.subscribe("user-y")
            _bus.publish("user-y", {"hello": "world"})
            payload = await asyncio.wait_for(q.get(), timeout=1.0)
            await _bus.unsubscribe("user-y", q)
            return payload

        out = asyncio.run(scenario())
        assert out == {"hello": "world"}


# ── M-50 + M-45 Blocker-fix Regression / New Feature tests ──────────────────


class TestTenantGuard:
    """The router's `_require_tenant()` and the service-level guard both must
    reject callers without a tenant context (HTTP 403 / ValueError respectively).
    """

    def test_list_comments_without_tenant_raises(self, db_session, case_entity) -> None:
        from app.domains.test_management import comments_service

        with pytest.raises(ValueError, match="tenant_id required"):
            comments_service.list_comments(
                db_session,
                entity_type=case_entity["entity_type"],
                entity_id=case_entity["entity_id"],
                tenant_id=None,
            )

    def test_router_require_tenant_returns_tenant_id(self) -> None:
        from app.domains.test_management.router import _require_tenant

        class _U:
            tenant_id = "00000000-0000-0000-0000-000000000001"

        assert _require_tenant(_U()) == "00000000-0000-0000-0000-000000000001"

    def test_router_require_tenant_none_raises_403(self) -> None:
        from fastapi import HTTPException

        from app.domains.test_management.router import _require_tenant

        class _U:
            tenant_id = None

        with pytest.raises(HTTPException) as exc:
            _require_tenant(_U())
        assert exc.value.status_code == 403

    def test_router_require_tenant_missing_attr_raises_403(self) -> None:
        from fastapi import HTTPException

        from app.domains.test_management.router import _require_tenant

        class _U:
            pass

        with pytest.raises(HTTPException) as exc:
            _require_tenant(_U())
        assert exc.value.status_code == 403


class TestChannelField:
    def test_allowed_channels_constant(self) -> None:
        from app.domains.test_management.comments_service import (
            ALLOWED_NOTIFICATION_CHANNELS,
        )

        assert ALLOWED_NOTIFICATION_CHANNELS == {
            "in_app",
            "email",
            "push",
            "slack",
            "teams",
        }

    def test_create_notification_in_app_channel(
        self, db_session, seeded_users, make_user
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        n = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(
                user_id=seeded_users["bob"],
                kind="system",
                title="t",
                body="b",
                channel="in_app",
            ),
            admin,
        )
        assert getattr(n, "channel", "in_app") == "in_app"

    def test_create_notification_email_channel_no_sse_publish(
        self, db_session, seeded_users, make_user, monkeypatch
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        publish_calls: list[tuple] = []
        monkeypatch.setattr(
            comments_service._bus,
            "publish",
            lambda uid, payload: publish_calls.append((uid, payload)),
        )

        admin = make_user(seeded_users["admin"])
        n = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(
                user_id=seeded_users["bob"],
                kind="system",
                title="email-channel",
                body="b",
                channel="email",
            ),
            admin,
        )
        assert getattr(n, "channel", "") == "email"
        # No SSE broadcast for non-in_app channels.
        assert publish_calls == []

    def test_create_notification_invalid_channel_coerced(
        self, db_session, seeded_users, make_user
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        admin = make_user(seeded_users["admin"])
        # Pydantic schema allows arbitrary str; service coerces unknown → in_app.
        n = comments_service.create_notification(
            db_session,
            MgmtNotificationCreate(
                user_id=seeded_users["bob"],
                kind="system",
                title="x",
                body="b",
                channel="totally-bogus",
            ),
            admin,
        )
        assert getattr(n, "channel", "in_app") == "in_app"


class TestRouteToChannel:
    @pytest.fixture()
    def fake_notif(self, seeded_users):
        # Use a simple stand-in object instead of touching the DB.
        class _N:
            def __init__(self, channel: str) -> None:
                self.id = "nid-" + channel
                self.user_id = seeded_users["bob"]
                self.project_id = None
                self.kind = "system"
                self.title = "t"
                self.body = "b"
                self.link_path = None
                self.severity = "info"
                self.source_trace = {}
                self.tenant_id = "00000000-0000-0000-0000-000000000001"
                self.read_at = None
                self.archived_at = None
                from datetime import datetime, timezone

                self.created_at = datetime.now(timezone.utc)
                self.channel = channel

        return _N

    def test_in_app_publishes_to_bus(self, fake_notif, monkeypatch) -> None:
        from app.domains.test_management import comments_service

        calls: list[tuple] = []
        monkeypatch.setattr(
            comments_service._bus,
            "publish",
            lambda uid, payload: calls.append((uid, payload)),
        )
        comments_service._route_to_channel(fake_notif("in_app"))
        assert len(calls) == 1

    @pytest.mark.parametrize("ch", ["email", "push", "slack", "teams"])
    def test_other_channels_do_not_publish(self, fake_notif, monkeypatch, ch) -> None:
        from app.domains.test_management import comments_service

        calls: list[tuple] = []
        monkeypatch.setattr(
            comments_service._bus,
            "publish",
            lambda uid, payload: calls.append((uid, payload)),
        )
        comments_service._route_to_channel(fake_notif(ch))
        assert calls == []


class TestSummarizeThread:
    def test_empty_thread_fallback(self, db_session, seeded_users, monkeypatch) -> None:
        from app.domains.test_management import comments_service

        # Force LLM unavailable so the deterministic fallback path runs.
        monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
        out = comments_service.summarize_thread(
            db_session,
            tenant_id=seeded_users["_tenants"]["alice"],
            entity_type="case",
            entity_id=str(uuid.uuid4()),
        )
        assert out["source"] == "fallback"
        assert out["comment_count"] == 0
        assert out["tldr"] == ""
        assert out["decisions"] == []
        assert out["openQuestions"] == []
        assert "generated_at" in out

    def test_fallback_with_comments(
        self, db_session, seeded_users, make_user, case_entity, monkeypatch
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
        alice = make_user(seeded_users["alice"])
        for i in range(3):
            comments_service.create_comment(
                db_session,
                MgmtCommentCreate(**case_entity, body_md=f"msg-{i}"),
                alice,
            )
        out = comments_service.summarize_thread(
            db_session,
            tenant_id=seeded_users["_tenants"]["alice"],
            entity_type=case_entity["entity_type"],
            entity_id=case_entity["entity_id"],
        )
        assert out["source"] == "fallback"
        assert out["comment_count"] == 3
        for key in (
            "tldr",
            "decisions",
            "openQuestions",
            "comment_count",
            "source",
            "generated_at",
            "entity_type",
            "entity_id",
        ):
            assert key in out

    def test_llm_branch_returns_source_llm(
        self, db_session, seeded_users, make_user, case_entity, monkeypatch
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtCommentCreate

        alice = make_user(seeded_users["alice"])
        comments_service.create_comment(
            db_session, MgmtCommentCreate(**case_entity, body_md="x"), alice
        )
        monkeypatch.setattr(
            comments_service,
            "_call_llm",
            lambda *a, **k: {
                "tldr": "fake tldr",
                "decisions": ["decided X"],
                "openQuestions": ["why?"],
            },
        )
        out = comments_service.summarize_thread(
            db_session,
            tenant_id=seeded_users["_tenants"]["alice"],
            entity_type=case_entity["entity_type"],
            entity_id=case_entity["entity_id"],
        )
        assert out["source"] == "llm"
        assert out["tldr"] == "fake tldr"
        assert out["decisions"] == ["decided X"]
        assert out["openQuestions"] == ["why?"]

    def test_invalid_entity_type_rejected(self, db_session, seeded_users) -> None:
        from app.domains.test_management import comments_service

        with pytest.raises(ValueError, match="entity_type"):
            comments_service.summarize_thread(
                db_session,
                tenant_id=seeded_users["_tenants"]["alice"],
                entity_type="invalid_type",
                entity_id=str(uuid.uuid4()),
            )


class TestDigestNotifications:
    def test_empty_notifications(self, db_session, seeded_users, monkeypatch) -> None:
        from app.domains.test_management import comments_service

        monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
        # Use an arbitrary user with no notifications.
        out = comments_service.digest_notifications(
            db_session,
            tenant_id=seeded_users["_tenants"]["alice"],
            user_id=str(uuid.uuid4()),
            window="24h",
        )
        assert out["groups"] == []
        assert out["source"] == "fallback"
        assert out["total_items"] == 0
        assert out["window"] == "24h"

    def test_fallback_groups_by_kind(
        self, db_session, seeded_users, make_user, monkeypatch
    ) -> None:
        from app.domains.test_management import comments_service
        from app.domains.test_management.schemas import MgmtNotificationCreate

        monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
        admin = make_user(seeded_users["admin"])
        # Mix two different kinds.
        for kind, title in (
            ("system", "Sys-1"),
            ("system", "Sys-2"),
            ("mention", "Ment-1"),
        ):
            comments_service.create_notification(
                db_session,
                MgmtNotificationCreate(
                    user_id=seeded_users["bob"], kind=kind, title=title
                ),
                admin,
            )
        out = comments_service.digest_notifications(
            db_session,
            tenant_id=seeded_users["_tenants"]["bob"],
            user_id=seeded_users["bob"],
            window="24h",
        )
        assert out["source"] == "fallback"
        assert out["total_items"] >= 3
        kinds_seen = {g["theme"].lower().replace(" ", "_") for g in out["groups"]}
        # Both kinds should show up as separate groups.
        assert "system" in kinds_seen
        assert "mention" in kinds_seen
        for g in out["groups"]:
            assert {"theme", "count", "oneLine"}.issubset(g.keys())

    def test_window_7d_accepted(self, db_session, seeded_users, monkeypatch) -> None:
        from app.domains.test_management import comments_service

        monkeypatch.setattr(comments_service, "_call_llm", lambda *a, **k: None)
        out = comments_service.digest_notifications(
            db_session,
            tenant_id=seeded_users["_tenants"]["alice"],
            user_id=str(uuid.uuid4()),
            window="7d",
        )
        assert out["window"] == "7d"


class TestRoutesRegistered:
    def test_summarize_and_digest_routes_registered(self) -> None:
        from app.domains.test_management.router import router

        paths = {route.path for route in router.routes}
        assert "/test-management/comments/summarize" in paths
        assert "/test-management/notifications/digest" in paths


class TestDeprecationHeaders:
    def test_deprecated_router_dependency_sets_headers(self) -> None:
        from fastapi import Response

        from app.domains.notifications.router import _mark_deprecated

        resp = Response()
        _mark_deprecated(resp)
        assert resp.headers.get("Deprecation") == "true"
        assert "Sunset" in resp.headers
        assert "Link" in resp.headers

    def test_router_has_dependency_attached(self) -> None:
        from app.domains.notifications.router import _mark_deprecated, router

        dep_funcs = [d.dependency for d in router.dependencies]
        assert _mark_deprecated in dep_funcs

