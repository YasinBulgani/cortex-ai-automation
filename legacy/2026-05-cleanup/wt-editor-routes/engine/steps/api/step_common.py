"""
steps/api/step_common.py — Tum feature dosyalarinda paylasilan ortak adimlar.

Bu dosya asagidaki reusable step'leri icerir:
  - Oturum yonetimi (login/anon)
  - HTTP yanit kodu kontrolleri
  - JSON alan dogrulamalari
  - Proje/senaryo olusturma
  - Genel assertion'lar
"""
from __future__ import annotations

import uuid

from pytest_bdd import given, when, then, parsers

from helpers.api_client import APIClient


# ============================================================================
# GIVEN — Ortak on kosullar
# ============================================================================

@given("backend servisi ayakta")
def backend_ready(api: APIClient):
    resp = api.get("/health")
    assert resp.status_code == 200


@given("admin kullanicisi seed edilmis")
def admin_seeded(api: APIClient):
    resp = api.get("/api/v1/auth/me")
    assert resp.status_code == 200


@given("kullanici oturum acmis")
def user_logged_in(api: APIClient):
    assert api.auth_headers, "Token mevcut degil — login basarisiz"


@given("kullanici oturum acmamis")
def user_not_logged_in(api_anon: APIClient, context: dict):
    context["client"] = api_anon


@given("bir test projesi olusturulmus")
def project_created(api: APIClient, project_id: str, context: dict):
    context["project_id"] = project_id


@given(parsers.parse('"{name}" isimli proje olusturulmus'))
def named_project_created(api: APIClient, context: dict, name: str):
    resp = api.post(api.tspm("projects"), json={"name": name})
    assert resp.status_code == 201
    context.setdefault("created_project_ids", []).append(resp.json()["id"])
    context["last_project_id"] = resp.json()["id"]


@given("projede bir senaryo olusturulmus")
def scenario_created(api: APIClient, project_id: str, scenario_id: str, context: dict):
    context["scenario_id"] = scenario_id


@given(parsers.parse('projede "{title}" baslikli senaryo olusturulmus'))
def named_scenario_created(api: APIClient, project_id: str, context: dict, title: str):
    resp = api.post(
        api.project_path(project_id, "scenarios"),
        json={"title": title, "description": "Test", "steps": []},
    )
    assert resp.status_code == 201
    context.setdefault("scenario_ids", []).append(resp.json()["id"])
    context["last_scenario_id"] = resp.json()["id"]
    context["last_scenario_title"] = title


@given(parsers.parse("projede en az {count:d} senaryo olusturulmus"))
def multiple_scenarios_created(api: APIClient, project_id: str, context: dict, count: int):
    ids = []
    for i in range(count):
        resp = api.post(
            api.project_path(project_id, "scenarios"),
            json={"title": f"Senaryo-{i + 1}", "steps": []},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    context["scenario_ids"] = ids


@given(parsers.parse("projede {count:d} senaryo olusturulmus"))
def exact_scenarios_created(api: APIClient, project_id: str, context: dict, count: int):
    ids = []
    for i in range(count):
        resp = api.post(
            api.project_path(project_id, "scenarios"),
            json={"title": f"Senaryo-{i + 1}", "steps": []},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    context["scenario_ids"] = ids


@given("projede en az 1 senaryo mevcut")
def at_least_one_scenario(api: APIClient, project_id: str, scenario_id: str, context: dict):
    context["scenario_id"] = scenario_id


@given("projede hic senaryo yok")
def no_scenarios(project_id: str):
    pass  # project_id fixture zaten bos proje olusturur


@given("projede bir gereksinim olusturulmus")
def requirement_created(api: APIClient, project_id: str, requirement_id: str, context: dict):
    context["requirement_id"] = requirement_id


# ============================================================================
# WHEN — Ortak istek adimlari
# ============================================================================

@when(parsers.parse('"{email}" ve "{password}" ile login istegi gonderilir'))
def login_request(api_anon: APIClient, context: dict, email: str, password: str):
    resp = api_anon.post("/api/v1/auth/login", json={"email": email, "password": password})
    context["response"] = resp


@when("/api/v1/auth/me endpoint'ine GET istegi gonderilir")
def get_me(api: APIClient, context: dict):
    context["response"] = api.get("/api/v1/auth/me")


@when("/api/v1/tspm/projects endpoint'ine token olmadan GET istegi gonderilir")
def get_projects_anon(api_anon: APIClient, context: dict):
    context["response"] = api_anon.get("/api/v1/tspm/projects")


# ============================================================================
# THEN — Ortak dogrulama adimlari
# ============================================================================

@then(parsers.parse("HTTP yanit kodu {code:d} olmalidir"))
def assert_status_code(context: dict, code: int):
    resp = context["response"]
    assert resp.status_code == code, (
        f"Beklenen: {code}, Gelen: {resp.status_code} — {resp.text[:500]}"
    )


@then("HTTP yanit kodu 401 veya 403 olmalidir")
def assert_unauthorized(context: dict):
    code = context["response"].status_code
    assert code in (401, 403), f"Beklenen: 401/403, Gelen: {code}"


@then(parsers.parse('yanit "{field}" alani dolu olmalidir'))
def assert_field_not_empty(context: dict, field: str):
    body = context["response"].json()
    assert body.get(field), f"'{field}' alani bos veya yok: {body}"


@then(parsers.parse('yanit "{field}" alani "{value}" olmalidir'))
def assert_field_equals_string(context: dict, field: str, value: str):
    body = context["response"].json()
    assert str(body.get(field)) == value, (
        f"'{field}': beklenen '{value}', gelen '{body.get(field)}'"
    )


@then(parsers.parse('yanit "{field}" alani {value:d} olmalidir'))
def assert_field_equals_int(context: dict, field: str, value: int):
    body = context["response"].json()
    assert body.get(field) == value, (
        f"'{field}': beklenen {value}, gelen {body.get(field)}"
    )


@then(parsers.parse('yanit "{field}" alani false olmalidir'))
def assert_field_false(context: dict, field: str):
    body = context["response"].json()
    assert body.get(field) is False, f"'{field}': beklenen False, gelen {body.get(field)}"


@then(parsers.parse('yanit "{field}" alani sayi olmalidir'))
def assert_field_is_number(context: dict, field: str):
    body = context["response"].json()
    assert isinstance(body.get(field), (int, float)), (
        f"'{field}' sayi degil: {body.get(field)}"
    )


@then(parsers.parse("yanit \"{field}\" alani 0'dan buyuk olmalidir"))
def assert_field_greater_than_zero(context: dict, field: str):
    body = context["response"].json()
    assert body.get(field, 0) > 0, f"'{field}' 0'dan buyuk degil: {body.get(field)}"


@then(parsers.parse('yanit hata mesaji "{text}" icermelidir'))
def assert_error_contains(context: dict, text: str):
    body = context["response"].text
    assert text in body, f"Hata mesajinda '{text}' bulunamadi: {body[:500]}"


@then(parsers.parse('yanit "{field}" listesi bos olmamalidir'))
def assert_list_not_empty(context: dict, field: str):
    body = context["response"].json()
    lst = body.get(field, [])
    assert len(lst) > 0, f"'{field}' listesi bos"


@then(parsers.parse('yanit listesinde her onay "{fields}" alanlarini icermelidir'))
def assert_list_items_have_fields(context: dict, fields: str):
    body = context["response"].json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    field_list = [f.strip().strip('"') for f in fields.split(",")]
    for item in items:
        for f in field_list:
            assert f in item, f"'{f}' alani eksik: {item}"
