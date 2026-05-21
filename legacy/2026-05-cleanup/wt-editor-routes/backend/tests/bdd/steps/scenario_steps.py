"""Step definitions for scenario_management.feature (Turkce Gherkin).

Bu modül senaryo CRUD, versiyonlama, arama, bulk silme ve izolasyon
senaryolarını kapsar. Ortak HTTP + assertion step'leri `auth_steps`
üzerinden geldiği için bu dosya yalnızca senaryo-özel adımları tanımlar.
"""

from __future__ import annotations

import re
from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when
from fastapi.testclient import TestClient

from ..conftest import unique

scenarios("../features/scenario_management.feature")


# ── Background: oturum + proje ───────────────────────────────────────


@given(parsers.parse('"{project_name}" adıyla bir proje mevcut'))
def ensure_project(api: TestClient, ctx: dict, project_name: str):
    unique_name = f"{project_name} {unique()}"
    r = api.post(
        "/api/v1/tspm/projects",
        json={"name": unique_name},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx["project_id"] = r.json()["id"]
    ctx["project_name"] = unique_name


# ── Senaryo oluşturma verisi ─────────────────────────────────────────


@given("senaryo oluşturma verisi hazırlanıyor")
def prepare_scenario_body(ctx: dict):
    ctx["scenario_body"] = {}


@given(parsers.re(r'senaryo başlığı "(?P<title>.*)" olarak belirleniyor'))
def set_scenario_title(ctx: dict, title: str):
    ctx.setdefault("scenario_body", {})["title"] = title


@given(parsers.re(r'senaryo açıklaması "(?P<desc>.*)" olarak belirleniyor'))
def set_scenario_desc(ctx: dict, desc: str):
    ctx.setdefault("scenario_body", {})["description"] = desc


@given("adımlar listesi hazırlanıyor:")
def set_scenario_steps(ctx: dict, datatable):
    """Gherkin data table'dan senaryo adımlarını parse eder.

    datatable: [[header1, header2, ...], [row1...], ...]
    Beklenen sütunlar: order | keyword | text
    """
    rows = list(datatable)
    headers = [h.strip().lower() for h in rows[0]]
    steps = []
    for row in rows[1:]:
        item = dict(zip(headers, [c.strip() for c in row]))
        steps.append(
            {
                "order": int(item.get("order", len(steps) + 1)),
                "keyword": item.get("keyword", "Given"),
                "text": item.get("text", ""),
            }
        )
    ctx.setdefault("scenario_body", {})["steps"] = steps


# ── Senaryo yaratma aksiyonu ─────────────────────────────────────────


@then(parsers.parse('proje altında POST "{suffix}" isteği gönderilir'))
@when(parsers.parse('proje altında POST "{suffix}" isteği gönderilir'))
def post_under_project(api: TestClient, ctx: dict, suffix: str):
    """`proje altında POST "…/scenarios"` — "…" prefix'i project_id ile doldurulur."""
    tail = suffix.lstrip(".").lstrip("/")
    path = f"/api/v1/tspm/projects/{ctx['project_id']}/{tail}"
    body = ctx.get("scenario_body") or ctx.get("body") or {}
    ctx["response"] = api.post(path, json=body, headers=ctx.get("headers", {}))


# ── Mevcut senaryo (update senaryosu için) ───────────────────────────


@given(parsers.parse('projede "{title}" başlıklı senaryo mevcut'))
def ensure_scenario(api: TestClient, ctx: dict, title: str):
    r = api.post(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios",
        json={"title": title},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx["scenario_id"] = r.json()["id"]
    ctx["scenario_title_original"] = title


@given(parsers.parse("senaryonun mevcut versiyonu {version:d}"))
def assert_scenario_version(api: TestClient, ctx: dict, version: int):
    r = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}",
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 200, r.text
    assert r.json().get("current_version") == version


@then(parsers.re(r'senaryo başlığı "(?P<title>.*)" olarak güncellenir'))
@when(parsers.re(r'senaryo başlığı "(?P<title>.*)" olarak güncellenir'))
def update_scenario_title(api: TestClient, ctx: dict, title: str):
    ctx["response"] = api.put(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}",
        json={"title": title},
        headers=ctx.get("headers", {}),
    )
    assert ctx["response"].status_code == 200, ctx["response"].text


@then(parsers.parse("senaryo versiyon listesinde versiyon {version:d} kaydı bulunmalı"))
def check_version_present(api: TestClient, ctx: dict, version: int):
    r = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}/versions",
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 200, r.text
    versions = r.json()
    # Response field adı `version_number` (alembic migration & ScenarioVersionOut)
    assert any(v.get("version_number") == version for v in versions), (
        f"versiyon {version} listede yok: {[v.get('version_number') for v in versions]}"
    )


@then(parsers.re(
    r'versiyon (?P<version>\d+) kaydında eski başlık "(?P<title>.*)" olmalı'
))
def check_version_title(api: TestClient, ctx: dict, version: str, title: str):
    r = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}/versions",
        headers=ctx.get("headers", {}),
    )
    vnum = int(version)
    target = next(
        (v for v in r.json() if v.get("version_number") == vnum), None
    )
    assert target is not None, f"versiyon {vnum} yok"
    snapshot_title = target.get("title")
    assert snapshot_title == title, f"v{vnum} başlığı: {snapshot_title!r}, beklenen: {title!r}"


# ── Arama senaryosu ─────────────────────────────────────────────────


@given("projede şu senaryolar mevcut:")
def seed_scenarios(api: TestClient, ctx: dict, datatable):
    rows = list(datatable)
    headers = [h.strip().lower() for h in rows[0]]
    title_col = "başlık" if "başlık" in headers else headers[0]
    idx = headers.index(title_col)
    ctx.setdefault("seeded_scenarios", [])
    for row in rows[1:]:
        title = row[idx].strip()
        r = api.post(
            f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios",
            json={"title": title},
            headers=ctx.get("headers", {}),
        )
        assert r.status_code == 201, r.text
        ctx["seeded_scenarios"].append({"id": r.json()["id"], "title": title})


@then(parsers.re(r'senaryo listesi "\?(?P<query>.*)" parametresiyle çağrılır'))
@when(parsers.re(r'senaryo listesi "\?(?P<query>.*)" parametresiyle çağrılır'))
def search_scenarios(api: TestClient, ctx: dict, query: str):
    ctx["response"] = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios?{query}",
        headers=ctx.get("headers", {}),
    )
    assert ctx["response"].status_code == 200, ctx["response"].text


@then(parsers.parse("yanıtta {count:d} senaryo dönmeli"))
def check_result_count(ctx: dict, count: int):
    got = ctx["response"].json()
    assert isinstance(got, list) and len(got) == count, (
        f"Beklenen {count}, dönen {len(got)}: {got}"
    )


@then(parsers.parse('yanıttaki tüm senaryoların başlığında "{token}" geçmeli'))
def check_all_titles_contain(ctx: dict, token: str):
    for item in ctx["response"].json():
        assert token.lower() in item.get("title", "").lower(), item


# ── Toplu silme senaryosu ────────────────────────────────────────────

_TRIPLE_RE = re.compile(r'"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"')


@given(parsers.parse('projede {n:d} senaryo oluşturulmuş: "{a}", "{b}", "{c}"'))
def seed_three_scenarios(api: TestClient, ctx: dict, n: int, a: str, b: str, c: str):
    names = [a, b, c][:n]
    ctx.setdefault("bulk_scenarios", {})
    for title in names:
        r = api.post(
            f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios",
            json={"title": title},
            headers=ctx.get("headers", {}),
        )
        assert r.status_code == 201, r.text
        ctx["bulk_scenarios"][title] = r.json()["id"]


@given("senaryoların ID'leri alınmış")
def ids_available(ctx: dict):
    assert ctx.get("bulk_scenarios"), "Önce senaryolar oluşturulmalı"


@then(parsers.re(
    r'"(?P<a>[^"]+)" ve "(?P<b>[^"]+)" senaryolarının ID\'leri ile bulk-delete isteği gönderilir'
))
@when(parsers.re(
    r'"(?P<a>[^"]+)" ve "(?P<b>[^"]+)" senaryolarının ID\'leri ile bulk-delete isteği gönderilir'
))
def bulk_delete(api: TestClient, ctx: dict, a: str, b: str):
    ids = [ctx["bulk_scenarios"][a], ctx["bulk_scenarios"][b]]
    ctx["response"] = api.post(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/bulk-delete",
        json={"ids": ids},
        headers=ctx.get("headers", {}),
    )


@then(parsers.re(r'senaryo listesinde yalnızca "(?P<remaining>[^"]+)" senaryosu kalmalı'))
def check_only_remaining(api: TestClient, ctx: dict, remaining: str):
    r = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios",
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 200
    titles = [s.get("title") for s in r.json()]
    assert titles == [remaining], f"Kalanlar: {titles}, beklenen: {[remaining]}"


# ── Proje izolasyonu senaryosu ───────────────────────────────────────


@given(parsers.parse('"{pa}" ve "{pb}" mevcut'))
def two_projects(api: TestClient, ctx: dict, pa: str, pb: str):
    ctx["projects"] = {}
    for name in (pa, pb):
        uname = f"{name}-{unique()}"
        r = api.post(
            "/api/v1/tspm/projects",
            json={"name": uname},
            headers=ctx.get("headers", {}),
        )
        assert r.status_code == 201, r.text
        ctx["projects"][name] = r.json()["id"]


@given(parsers.parse('"{pname}" altında "{sname}" senaryosu var'))
def scenario_under_project(api: TestClient, ctx: dict, pname: str, sname: str):
    pid = ctx["projects"][pname]
    r = api.post(
        f"/api/v1/tspm/projects/{pid}/scenarios",
        json={"title": sname},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx.setdefault("cross_scenarios", {})[(pname, sname)] = r.json()["id"]


@then(parsers.re(
    r'"(?P<pother>[^"]+)" ID\'si ile "(?P<sname>[^"]+)" senaryosuna erişim denenir'
))
@when(parsers.re(
    r'"(?P<pother>[^"]+)" ID\'si ile "(?P<sname>[^"]+)" senaryosuna erişim denenir'
))
def cross_project_access(api: TestClient, ctx: dict, pother: str, sname: str):
    pother_id = ctx["projects"][pother]
    # Senaryo hangi projede oluşturulmuşsa onun id'sini biliyoruz
    scenario_id = next(
        v for (p, s), v in ctx["cross_scenarios"].items() if s == sname and p != pother
    )
    ctx["response"] = api.get(
        f"/api/v1/tspm/projects/{pother_id}/scenarios/{scenario_id}",
        headers=ctx.get("headers", {}),
    )


@given(parsers.parse('"{pname}" altında "{sname}" var'))
def scenario_under_project_alt(api: TestClient, ctx: dict, pname: str, sname: str):
    scenario_under_project(api, ctx, pname, sname)


@then(parsers.re(
    r'"(?P<pname>[^"]+)" altında "(?P<sname>[^"]+)"nun ID\'si ile bulk-delete gönderilir'
))
@when(parsers.re(
    r'"(?P<pname>[^"]+)" altında "(?P<sname>[^"]+)"nun ID\'si ile bulk-delete gönderilir'
))
def bulk_delete_cross(api: TestClient, ctx: dict, pname: str, sname: str):
    pid = ctx["projects"][pname]
    # sname hangi projede oluşturulduysa onun id'si
    sid = next(
        v for (p, s), v in ctx["cross_scenarios"].items() if s == sname
    )
    ctx["response"] = api.post(
        f"/api/v1/tspm/projects/{pid}/scenarios/bulk-delete",
        json={"ids": [sid]},
        headers=ctx.get("headers", {}),
    )


@then(parsers.parse('"{pname}" altında "{sname}" hâlâ mevcut olmalı'))
def check_scenario_still_exists(api: TestClient, ctx: dict, pname: str, sname: str):
    pid = ctx["projects"][pname]
    sid = next(
        v for (p, s), v in ctx["cross_scenarios"].items() if s == sname and p == pname
    )
    r = api.get(
        f"/api/v1/tspm/projects/{pid}/scenarios/{sid}",
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 200, f"Senaryo silinmiş: {r.status_code}"


# ── Diff senaryosu ───────────────────────────────────────────────────


@given("projede senaryo mevcut ve 2 kez güncellenmiş")
def scenario_with_2_updates(api: TestClient, ctx: dict):
    """Senaryo create + 2 ardışık update ⇒ v1 & v2 snapshot'ları oluşur.

    Backend mantığı: update öncesi `current_version` değeriyle snapshot saklanır.
    - create: current_version=1 (henüz snapshot yok)
    - update #1: v1 snapshot (Orijinal), current_version=2
    - update #2: v2 snapshot (Güncel), current_version=3
    """
    r = api.post(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios",
        json={"title": "Orijinal Başlık"},
        headers=ctx.get("headers", {}),
    )
    assert r.status_code == 201, r.text
    ctx["scenario_id"] = r.json()["id"]

    r2 = api.put(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}",
        json={"title": "Güncel Başlık"},
        headers=ctx.get("headers", {}),
    )
    assert r2.status_code == 200, r2.text

    r3 = api.put(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}",
        json={"title": "Üçüncü Başlık"},
        headers=ctx.get("headers", {}),
    )
    assert r3.status_code == 200, r3.text


@given(parsers.re(r'versiyon (?P<vnum>\d+) başlığı "(?P<title>.*)"'))
def version_title_given(ctx: dict, vnum: str, title: str):
    ctx.setdefault("expected_versions", {})[int(vnum)] = title


@then("versiyon 1 ve 2 diff endpoint'i çağrılır")
@when("versiyon 1 ve 2 diff endpoint'i çağrılır")
def call_version_diff(api: TestClient, ctx: dict):
    ctx["response"] = api.get(
        f"/api/v1/tspm/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}/versions/1/diff/2",
        headers=ctx.get("headers", {}),
    )
    assert ctx["response"].status_code == 200, ctx["response"].text


@then(parsers.parse('yanıtta "{field}" değeri true olmalı'))
def check_true(ctx: dict, field: str):
    assert ctx["response"].json().get(field) is True


@then(parsers.re(r'yanıtta "(?P<f1>[^"]+)" ve "(?P<f2>[^"]+)" dolu olmalı'))
def check_two_fields_present(ctx: dict, f1: str, f2: str):
    body = ctx["response"].json()
    assert body.get(f1), f"{f1} boş: {body}"
    assert body.get(f2), f"{f2} boş: {body}"
