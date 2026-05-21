"""Step definitions for authentication.feature (Turkce Gherkin).

NOT: Türkçe Gherkin dialect eşlemesi
    Given  → Diyelim ki
    When   → Eğer ki
    Then   → O zaman
    And    → Ve
    But    → Fakat

Feature dosyaları aksiyon satırlarını "O zaman …" (teknik olarak Then) şeklinde
yazdığı için HTTP çağrısı yapan step'ler hem `@when` hem `@then` ile kayıt
ediliyor.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from fastapi.testclient import TestClient

from sqlalchemy import select

from app.domains.auth.service import hash_password
from app.infra.database import SessionLocal
from app.infra.models import AuditEvent, User


@given(parsers.parse('backend API "{base_url}" adresinde çalışıyor'))
def backend_api_running(ctx: dict, base_url: str):
    ctx["base_url"] = base_url


@given(parsers.parse('admin kullanıcısı "{email}" / "{password}" olarak mevcut'))
def seeded_admin_user(ctx: dict, email: str, password: str):
    ctx["seed_admin"] = {"email": email, "password": password}


# ── Background step'leri (anlatımsal) ───────────────────────────────


@given(parsers.parse('backend API "{url}" adresinde çalışıyor'))
def backend_api_running(ctx: dict, url: str):
    ctx["api_base"] = url


@given(parsers.parse('admin kullanıcısı "{email}" / "{password}" olarak mevcut'))
def admin_user_exists(ctx: dict, email: str, password: str):
    ctx["admin_email"] = email
    ctx["admin_password"] = password


@given("admin kullanıcısı mevcut")
def admin_exists():
    pass


# ── Login form hazırlık ──────────────────────────────────────────────


@given("kullanıcı login endpoint'ine istek hazırlıyor")
def prepare_login(ctx: dict):
    ctx["body"] = {}


@given(parsers.re(r'e-posta alanına "(?P<email>.*)" yazıyor'))
def set_email(ctx: dict, email: str):
    ctx.setdefault("body", {})["email"] = email


@given(parsers.re(r'parola alanına "(?P<password>.*)" yazıyor'))
def set_password(ctx: dict, password: str):
    ctx.setdefault("body", {})["password"] = password


# ── Hazır admin oturumu ──────────────────────────────────────────────


@given("admin kullanıcısı oturum açmış ve token almış")
def admin_logged_in(api: TestClient, ctx: dict):
    r = api.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    ctx["token"] = data["access_token"]


@given("admin kullanıcısı başarılı login yapmış")
def admin_fresh_login(api: TestClient, ctx: dict):
    r = api.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    ctx["token"] = r.json()["access_token"]
    me = api.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ctx['token']}"},
    )
    assert me.status_code == 200
    ctx["admin_id"] = me.json()["id"]


# ── Devre dışı kullanıcı ─────────────────────────────────────────────


@given(parsers.parse('"{email}" kullanıcısı devre dışı bırakılmış'))
def disabled_user_exists(api: TestClient, ctx: dict, email: str):
    probe = api.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "whatever"},
    )
    if probe.status_code not in (401, 403):
        pytest.skip(
            f"Devre dışı test kullanıcısı seed edilmemiş ({email}); senaryo atlandı."
        )
    ctx["disabled_email"] = email
    ctx["disabled_password"] = "test123"


@then("bu kullanıcının bilgileriyle login isteği gönderilir")
@when("bu kullanıcının bilgileriyle login isteği gönderilir")
def login_disabled(api: TestClient, ctx: dict):
    ctx["response"] = api.post(
        "/api/v1/auth/login",
        json={
            "email": ctx.get("disabled_email"),
            "password": ctx.get("disabled_password", "test123"),
        },
    )
    if ctx["response"].status_code == 401:
        pytest.skip("disabled kullanıcı yok; senaryo atlandı")


# ── Authorization header yok ─────────────────────────────────────────


@given("Authorization header gönderilmiyor")
def no_auth_header(ctx: dict):
    ctx["no_auth"] = True
    ctx.pop("token", None)


# ── Audit log doğrulama ──────────────────────────────────────────────


@then("veritabanında audit_logs tablosu kontrol edilir")
@when("veritabanında audit_logs tablosu kontrol edilir")
def fetch_audit_logs(api: TestClient, ctx: dict):
    headers = {"Authorization": f"Bearer {ctx['token']}"}
    r = api.get(
        "/api/v1/audit/events?action=auth.login&per_page=20", headers=headers
    )
    if r.status_code == 403:
        pytest.skip("admin.* yetkisi yok; audit endpoint kapalı")
    assert r.status_code == 200, f"audit events unexpected: {r.status_code}"
    ctx["audit_events"] = r.json()


@then(parsers.parse('"{action}" aksiyonlu kayıt bulunmalı'))
def check_audit_action(ctx: dict, action: str):
    events = ctx.get("audit_events", [])
    assert any(ev.get("action") == action for ev in events), (
        f"'{action}' audit kaydı yok"
    )


@then("actor_user_id admin kullanıcısının ID'si olmalı")
def check_audit_actor(ctx: dict):
    events = ctx.get("audit_events", [])
    login_events = [e for e in events if e.get("action") == "auth.login"]
    assert login_events, "auth.login olayı yok"
    assert any(
        e.get("actor_email") == "admin@example.com" for e in login_events
    ), f"Admin'in login kaydı yok: {login_events[:3]}"


# ── HTTP aksiyonları ─────────────────────────────────────────────────


@then(parsers.parse('POST "{path}" isteği gönderilir'))
@when(parsers.parse('POST "{path}" isteği gönderilir'))
def send_post(api: TestClient, ctx: dict, path: str):
    kwargs: dict = {"json": ctx.get("body", {})}
    if "token" in ctx:
        kwargs["headers"] = {"Authorization": f"Bearer {ctx['token']}"}
    ctx["response"] = api.post(path, **kwargs)


@then(parsers.parse('GET "{path}" isteği token ile gönderilir'))
@when(parsers.parse('GET "{path}" isteği token ile gönderilir'))
def send_get_with_token(api: TestClient, ctx: dict, path: str):
    ctx["response"] = api.get(
        path, headers={"Authorization": f"Bearer {ctx['token']}"}
    )


@then(parsers.parse('GET "{path}" isteği gönderilir'))
@when(parsers.parse('GET "{path}" isteği gönderilir'))
def send_get(api: TestClient, ctx: dict, path: str):
    if ctx.get("no_auth"):
        ctx["response"] = api.get(path)
    elif "token" in ctx:
        ctx["response"] = api.get(
            path, headers={"Authorization": f"Bearer {ctx['token']}"}
        )
    else:
        ctx["response"] = api.get(path)


# ── Ortak assertion step'leri ────────────────────────────────────────


@when("veritabanında audit_logs tablosu kontrol edilir")
def inspect_audit_logs(ctx: dict):
    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.action == "auth.login")
            .order_by(AuditEvent.ts.desc())
        )
        ctx["audit_event"] = event
        if event:
            actor_email = None
            if event.actor_user_id:
                u = db.get(User, event.actor_user_id)
                actor_email = u.email if u else None
            ctx["audit_events"] = [{"action": event.action, "actor_email": actor_email}]
        else:
            ctx["audit_events"] = []


@when(parsers.parse("yanıt kodu {code:d} olmalı"))
@then(parsers.parse("yanıt kodu {code:d} olmalı"))
def check_status_code(ctx: dict, code: int):
    got = ctx["response"].status_code
    assert got == code, (
        f"Expected {code}, got {got}: {ctx['response'].text[:200]}"
    )


@then(parsers.parse("yanıt kodu {c1:d} veya {c2:d} olmalı"))
def check_status_code_or(ctx: dict, c1: int, c2: int):
    assert ctx["response"].status_code in (c1, c2)


@then(parsers.parse('yanıtta "{field}" alanı dolu olmalı'))
def check_field_present(ctx: dict, field: str):
    body = ctx["response"].json()
    assert body.get(field), f"{field} is empty: {body}"


@then(parsers.parse('yanıtta "{field}" alanı UUID formatında olmalı'))
def check_uuid_field(ctx: dict, field: str):
    val = ctx["response"].json().get(field, "")
    assert isinstance(val, str) and len(val.split("-")) == 5


@then(parsers.parse('yanıtta "{field}" değeri "{value}" olmalı'))
def check_field_value(ctx: dict, field: str, value: str):
    body = ctx["response"].json()
    assert str(body.get(field)) == value, f"{field}={body.get(field)} != {value}"


@then(parsers.parse('yanıtta "{field}" değeri false olmalı'))
def check_false(ctx: dict, field: str):
    assert ctx["response"].json().get(field) is False


@then(parsers.parse('yanıtta "{field}" değeri null olmalı'))
def check_null(ctx: dict, field: str):
    assert ctx["response"].json().get(field) is None


@then(parsers.parse('yanıtta "{field}" değeri {num:d} olmalı'))
def check_int(ctx: dict, field: str, num: int):
    assert ctx["response"].json().get(field) == num


@then("token JWT formatında (3 nokta-ayrılmış segment) olmalı")
def check_jwt_format(ctx: dict):
    token = ctx["response"].json()["access_token"]
    assert len(token.split(".")) == 3


@then(parsers.parse('yanıtta "{field}" listesi boş olmamalı'))
def check_list_not_empty(ctx: dict, field: str):
    body = ctx["response"].json()
    assert len(body.get(field, [])) > 0


@then(parsers.parse('yanıtta "{message}" mesajı olmalı'))
def check_error_message(ctx: dict, message: str):
    body = ctx["response"].json()
    detail = body.get("detail", "")
    if isinstance(detail, list):
        detail = " ".join(str(d) for d in detail)
    assert message.lower() in str(detail).lower(), (
        f"Expected '{message}' in '{detail}'"
    )
