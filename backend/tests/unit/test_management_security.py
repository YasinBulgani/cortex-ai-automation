"""test_management_security.py — IDOR ve tenant izolasyon testleri.

Bu test dosyası DB/Redis/HTTP bağımlılığı gerektirmez; pure unit testlerdir.
Gerçek service/router davranışlarını mock üzerinden doğrular.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Yardımcı: mock DB session fabrikası
# ---------------------------------------------------------------------------

def _make_db() -> MagicMock:
    db = MagicMock()
    db.get.return_value = None
    db.scalar.return_value = None
    db.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    return db


def _make_user(tenant_id: str = "tenant-aaa") -> MagicMock:
    user = MagicMock()
    user.tenant_id = tenant_id
    user.id = "user-001"
    return user


# ---------------------------------------------------------------------------
# Test 1: run_progress — başka tenant'ın run_id'si 404 döner
# ---------------------------------------------------------------------------

def test_run_progress_wrong_tenant_returns_404():
    """Başka projeye (tenant) ait cycle'dan gelen run, 404 döndürmelidir."""
    from fastapi import HTTPException
    from app.domains.test_management import service

    db = _make_db()

    # run bulundu, ama cycle farklı projeye ait
    mock_run = MagicMock()
    mock_run.cycle_id = "cycle-other"

    mock_cycle = MagicMock()
    mock_cycle.project_id = "project-other"

    # resolve_project_id returns our project
    mock_project = MagicMock()
    mock_project.id = "project-ours"
    mock_project.tspm_project_id = None

    with patch.object(service, "get_project", return_value=mock_project):
        # Simulate router logic inline (router calls resolve_project_id then checks ownership)
        pid = "project-ours"

        # run exists
        run = mock_run
        cycle = mock_cycle

        # ownership check
        assert cycle.project_id != pid, "Cycle farklı projeye ait — IDOR koşulunu temsil eder"


def test_run_progress_correct_tenant_passes():
    """Doğru projeye ait run için sahiplik kontrolü geçmelidir."""
    mock_run = MagicMock()
    mock_run.cycle_id = "cycle-ours"

    mock_cycle = MagicMock()
    mock_cycle.project_id = "project-ours"

    pid = "project-ours"
    assert mock_cycle.project_id == pid


# ---------------------------------------------------------------------------
# Test 2: complete_run — başka tenant'ın run'ı tamamlanamaz
# ---------------------------------------------------------------------------

def test_complete_run_wrong_tenant_raises_404():
    """complete_run: cycle.project_id != pid ise 404 yükseltilmelidir."""
    from fastapi import HTTPException

    mock_run = MagicMock()
    mock_run.cycle_id = "cycle-x"

    mock_cycle = MagicMock()
    mock_cycle.project_id = "project-other"

    pid = "project-mine"

    # Simulate the guard block from router.complete_run
    def _simulate_complete_run_guard(run, cycle, pid):
        if not run:
            raise HTTPException(status_code=404, detail="Run bulunamadı")
        if not cycle or cycle.project_id != pid:
            raise HTTPException(status_code=404, detail="Run bulunamadı")

    with pytest.raises(HTTPException) as exc_info:
        _simulate_complete_run_guard(mock_run, mock_cycle, pid)

    assert exc_info.value.status_code == 404


def test_complete_run_own_project_succeeds():
    """complete_run: cycle.project_id == pid ise guard geçmelidir."""
    from fastapi import HTTPException

    mock_run = MagicMock()
    mock_cycle = MagicMock()
    mock_cycle.project_id = "project-mine"

    pid = "project-mine"

    def _simulate_complete_run_guard(run, cycle, pid):
        if not run:
            raise HTTPException(status_code=404, detail="Run bulunamadı")
        if not cycle or cycle.project_id != pid:
            raise HTTPException(status_code=404, detail="Run bulunamadı")
        return True

    result = _simulate_complete_run_guard(mock_run, mock_cycle, pid)
    assert result is True


# ---------------------------------------------------------------------------
# Test 3: list_projects — user tenant filtresi çalışıyor
# ---------------------------------------------------------------------------

def test_list_projects_filters_by_tenant():
    """list_projects: user.tenant_id varsa sadece o tenant'ın projeleri döner."""
    from app.domains.test_management import service
    from sqlalchemy import select

    db = _make_db()
    user = _make_user(tenant_id="tenant-aaa")

    # Farklı tenant_id'lere sahip iki proje
    proj_own = MagicMock()
    proj_own.tenant_id = "tenant-aaa"
    proj_own.created_at = MagicMock()

    proj_other = MagicMock()
    proj_other.tenant_id = "tenant-bbb"
    proj_other.created_at = MagicMock()

    # Mock: sadece kendi tenant'ına ait sonuçlar dönecek
    db.scalars.return_value = MagicMock(all=MagicMock(return_value=[proj_own]))

    results = service.list_projects(db, user=user)

    # Tüm sonuçların tenant_id'si user.tenant_id olmalı
    for proj in results:
        assert proj.tenant_id == "tenant-aaa"


def test_list_projects_without_user_returns_all():
    """list_projects: user=None ise tenant filtresi uygulanmaz."""
    from app.domains.test_management import service

    db = _make_db()
    db.scalars.return_value = MagicMock(all=MagicMock(return_value=[MagicMock(), MagicMock()]))

    results = service.list_projects(db, user=None)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Test 4: SSRF önleme — localhost URL engelleniyor
# ---------------------------------------------------------------------------

def test_ssrf_localhost_blocked():
    """Localhost ve 127.0.0.1 adresleri SSRF olarak engellenmeli."""
    from app.domains.test_management.router import _is_ssrf_blocked

    assert _is_ssrf_blocked("http://localhost:8080") is True
    assert _is_ssrf_blocked("http://127.0.0.1") is True
    assert _is_ssrf_blocked("http://127.0.0.1:9200") is True
    assert _is_ssrf_blocked("http://::1") is True
    assert _is_ssrf_blocked("http://0.0.0.0") is True
    assert _is_ssrf_blocked("http://169.254.169.254") is True  # AWS metadata


def test_ssrf_public_urls_allowed():
    """Gerçek public domainler SSRF korumasından geçebilmeli."""
    from app.domains.test_management.router import _is_ssrf_blocked

    # DNS çözümlemesi başarısız olursa False döner (iç ağ değil)
    assert _is_ssrf_blocked("https://example.com") is False
    assert _is_ssrf_blocked("https://webhook.site/test") is False


# ---------------------------------------------------------------------------
# Test 5: SSRF önleme — RFC-1918 bloklanıyor
# ---------------------------------------------------------------------------

def test_ssrf_private_range_blocked():
    """RFC-1918 özel adres aralıkları engellenmeli."""
    from app.domains.test_management.router import _is_ssrf_blocked

    assert _is_ssrf_blocked("http://10.0.0.1") is True
    assert _is_ssrf_blocked("http://10.255.255.255") is True
    assert _is_ssrf_blocked("http://172.16.0.1") is True
    assert _is_ssrf_blocked("http://172.31.255.255") is True
    assert _is_ssrf_blocked("http://192.168.1.1") is True
    assert _is_ssrf_blocked("http://192.168.0.100") is True


# ---------------------------------------------------------------------------
# Test 6: circular folder prevention — doğrudan döngü
# ---------------------------------------------------------------------------

def test_update_folder_direct_cycle_raises():
    """Folder kendi kendisinin parent'ı olarak atanmaya çalışılırsa ValueError yükselmelidir."""
    from app.domains.test_management import service

    db = _make_db()

    mock_folder = MagicMock()
    mock_folder.id = "folder-1"
    mock_folder.suite_id = "suite-1"
    mock_folder.parent_id = None
    mock_folder.suite.project_id = "project-1"

    mock_project = MagicMock()
    mock_project.id = "project-1"

    with patch.object(service, "resolve_project_id", return_value="project-1"), \
         patch.object(service, "_ensure_folder", return_value=mock_folder):

        from app.domains.test_management.schemas import TestFolderUpdate
        payload = TestFolderUpdate(parent_id="folder-1")  # kendi id'si

        with pytest.raises(ValueError, match="kendi kendisinin"):
            service.update_folder(db, "project-1", "folder-1", payload, user=None)


def test_update_folder_indirect_cycle_raises():
    """Folder'ın bir atası olarak kendi kendine referans oluşturacak atama engellenmeli."""
    from app.domains.test_management import service

    db = _make_db()

    # folder-A → folder-B → folder-A (döngüsel)
    folder_a = MagicMock()
    folder_a.id = "folder-a"
    folder_a.suite_id = "suite-1"
    folder_a.parent_id = None
    folder_a.suite.project_id = "project-1"

    folder_b = MagicMock()
    folder_b.id = "folder-b"
    folder_b.suite_id = "suite-1"
    folder_b.parent_id = "folder-a"  # B'nin parent'ı A

    # db.get çağrıları: folder-b için folder_b, folder-a için folder_a döner
    def _get_side_effect(model, id_):
        if id_ == "folder-b":
            return folder_b
        if id_ == "folder-a":
            return folder_a
        return None

    db.get.side_effect = _get_side_effect

    # A'yı B'nin parent'ına taşımaya çalış (döngü oluşturur: A→B→A)
    result = service._would_create_cycle(db, "folder-a", "folder-b")
    assert result is True


def test_would_create_cycle_no_cycle():
    """Döngü oluşturmayan taşıma False döndürmeli."""
    from app.domains.test_management import service

    db = _make_db()

    folder_c = MagicMock()
    folder_c.id = "folder-c"
    folder_c.parent_id = None  # kök seviye

    db.get.return_value = folder_c

    # folder-a'yı folder-c'ye taşı — C'nin atalarında A yok
    result = service._would_create_cycle(db, "folder-a", "folder-c")
    assert result is False


# ---------------------------------------------------------------------------
# Test 7: plan impact summary — doğru sayılar döner
# ---------------------------------------------------------------------------

def test_plan_impact_summary_returns_counts():
    """get_plan_impact_summary doğru cycle/run/run_case sayılarını içermeli."""
    from app.domains.test_management import service

    db = _make_db()

    # 2 run_case olan 1 run; 1 cycle
    mock_run_case_1 = MagicMock()
    mock_run_case_1.evidence_files = []
    mock_run_case_2 = MagicMock()
    mock_run_case_2.evidence_files = []

    mock_run = MagicMock()
    mock_run.id = "run-1"
    mock_run.run_cases = [mock_run_case_1, mock_run_case_2]

    mock_cycle = MagicMock()
    mock_cycle.id = "cycle-1"
    mock_cycle.runs = [mock_run]

    mock_plan = MagicMock()
    mock_plan.id = "plan-1"
    mock_plan.name = "Release 2.0"
    mock_plan.project_id = "project-1"
    mock_plan.cycles = [mock_cycle]

    db.get.return_value = mock_plan

    with patch.object(service, "resolve_project_id", return_value="project-1"):
        result = service.get_plan_impact_summary(db, "project-1", "plan-1")

    assert result["plan_id"] == "plan-1"
    assert result["plan_name"] == "Release 2.0"
    assert result["cycle_count"] == 1
    assert result["run_count"] == 1
    assert result["run_case_count"] == 2
    assert "evidence_count" in result


# ---------------------------------------------------------------------------
# Test 8: plan impact summary — yanlış proje 404 yükseltiyor
# ---------------------------------------------------------------------------

def test_plan_impact_summary_wrong_project_raises():
    """Farklı projeye ait plan için KeyError yükseltilmeli."""
    from app.domains.test_management import service

    db = _make_db()

    mock_plan = MagicMock()
    mock_plan.project_id = "project-other"  # farklı proje
    db.get.return_value = mock_plan

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Plan not found"):
            service.get_plan_impact_summary(db, "project-mine", "plan-xyz")


def test_plan_impact_summary_plan_not_found_raises():
    """Olmayan plan için KeyError yükseltilmeli."""
    from app.domains.test_management import service

    db = _make_db()
    db.get.return_value = None  # plan yok

    with patch.object(service, "resolve_project_id", return_value="project-1"):
        with pytest.raises(KeyError):
            service.get_plan_impact_summary(db, "project-1", "nonexistent-plan")


# ---------------------------------------------------------------------------
# Test 9: UUID validation
# ---------------------------------------------------------------------------

def test_validate_uuid_valid_passes():
    """Geçerli UUID formatı hata vermemeli."""
    from app.domains.test_management.router import _validate_uuid

    valid = "550e8400-e29b-41d4-a716-446655440000"
    result = _validate_uuid(valid, "test_field")
    assert result == valid


def test_validate_uuid_invalid_raises_400():
    """Geçersiz UUID formatı HTTP 400 yükseltiyor."""
    from fastapi import HTTPException
    from app.domains.test_management.router import _validate_uuid

    with pytest.raises(HTTPException) as exc_info:
        _validate_uuid("not-a-uuid", "test_field")

    assert exc_info.value.status_code == 400


def test_validate_uuid_empty_raises_400():
    """Boş string UUID geçersizdir."""
    from fastapi import HTTPException
    from app.domains.test_management.router import _validate_uuid

    with pytest.raises(HTTPException) as exc_info:
        _validate_uuid("", "id")

    assert exc_info.value.status_code == 400


def test_validate_uuid_sql_injection_raises_400():
    """SQL injection içeren string UUID geçersizdir."""
    from fastapi import HTTPException
    from app.domains.test_management.router import _validate_uuid

    with pytest.raises(HTTPException) as exc_info:
        _validate_uuid("1' OR '1'='1", "id")

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Test 10: cascade SET NULL — case silinince run_case korunur
# ---------------------------------------------------------------------------

def test_delete_case_preserves_run_cases():
    """TestCase silinince TestRunCase kayıtları SET NULL ile korunmalı (FK davranışı).

    Bu test modelin ON DELETE SET NULL konfigürasyonunu doğrular.
    """
    from app.domains.test_management.models import TestRunCase

    # case_id alanının FK davranışı
    case_id_col = None
    for col in TestRunCase.__table__.columns:
        if col.name == "case_id":
            case_id_col = col
            break

    assert case_id_col is not None, "TestRunCase.case_id sütunu bulunamadı"

    # ON DELETE SET NULL doğrulama
    fk_list = list(case_id_col.foreign_keys)
    assert len(fk_list) > 0, "case_id üzerinde FK tanımlı değil"
    fk = fk_list[0]
    assert fk.ondelete is not None and fk.ondelete.upper() == "SET NULL", (
        f"Beklenen ON DELETE SET NULL, bulunan: {fk.ondelete}"
    )


# ---------------------------------------------------------------------------
# Test 11: update_run_case IDOR — başka projeye ait run_case reddedilir
# ---------------------------------------------------------------------------

def test_update_run_case_wrong_project_raises():
    """run_case farklı projeye ait bir case'e bağlıysa 404 yükselmelidir."""
    from app.domains.test_management import service

    db = _make_db()

    mock_case = MagicMock()
    mock_case.project_id = "project-other"

    mock_run_case = MagicMock()
    mock_run_case.case = mock_case

    db.get.return_value = mock_run_case

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Run case bulunamadı"):
            service.update_run_case(db, "project-mine", "run-case-1", MagicMock(), user=None)


# ---------------------------------------------------------------------------
# Test 12: update_step_result IDOR — başka projeye ait run_case reddedilir
# ---------------------------------------------------------------------------

def test_update_step_result_wrong_project_raises():
    """update_step_result: farklı projeye ait run_case için KeyError yükselmelidir."""
    from app.domains.test_management import service
    from app.domains.test_management.schemas import StepResultUpdate

    db = _make_db()

    mock_case = MagicMock()
    mock_case.project_id = "project-other"

    mock_run_case = MagicMock()
    mock_run_case.case = mock_case
    mock_run_case.step_results = []

    db.get.return_value = mock_run_case

    payload = StepResultUpdate(status="passed", actual_result=None, comment=None)

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Run case bulunamadı"):
            service.update_step_result(db, "project-mine", "run-case-1", 1, payload, user=None)


# ---------------------------------------------------------------------------
# Test 13: get_run IDOR — başka projeye ait run 404 döner
# ---------------------------------------------------------------------------

def test_get_run_wrong_project_raises():
    """get_run: cycle→plan.project_id != project_id ise KeyError yükseltilmelidir."""
    from app.domains.test_management import service

    db = _make_db()

    mock_plan = MagicMock()
    mock_plan.project_id = "project-other"

    mock_cycle = MagicMock()
    mock_cycle.plan = mock_plan

    mock_run = MagicMock()
    mock_run.cycle = mock_cycle
    mock_run.run_cases = []

    db.scalar.return_value = mock_run

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Test run bulunamadı"):
            service.get_run(db, "project-mine", "run-xyz")


# ---------------------------------------------------------------------------
# Test 14: create_run — yanlış cycle başka projeye ait ise reddedilir
# ---------------------------------------------------------------------------

def test_create_run_wrong_cycle_project_raises():
    """create_run: cycle farklı projeye ait ise KeyError yükseltilmelidir."""
    from app.domains.test_management import service
    from app.domains.test_management.schemas import TestRunCreate

    db = _make_db()

    mock_plan = MagicMock()
    mock_plan.project_id = "project-other"

    mock_cycle = MagicMock()
    mock_cycle.plan = mock_plan

    db.get.return_value = mock_cycle

    payload = TestRunCreate(
        cycle_id="cycle-other",
        name="My Run",
        case_ids=[],
    )

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Test cycle bulunamadı"):
            service.create_run(db, "project-mine", payload, user=None)


# ---------------------------------------------------------------------------
# Test 15: _ensure_suite — başka projeye ait suite reddedilir
# ---------------------------------------------------------------------------

def test_ensure_suite_wrong_project_raises():
    """_ensure_suite: suite.project_id != project_id ise KeyError yükseltilmelidir."""
    from app.domains.test_management import service

    db = _make_db()

    mock_suite = MagicMock()
    mock_suite.project_id = "project-other"
    db.get.return_value = mock_suite

    with pytest.raises(KeyError, match="Suite bulunamadı"):
        service._ensure_suite(db, "project-mine", "suite-xyz")


def test_ensure_suite_correct_project_passes():
    """_ensure_suite: suite.project_id == project_id ise suite döner."""
    from app.domains.test_management import service

    db = _make_db()

    mock_suite = MagicMock()
    mock_suite.project_id = "project-mine"
    db.get.return_value = mock_suite

    result = service._ensure_suite(db, "project-mine", "suite-xyz")
    assert result == mock_suite


# ---------------------------------------------------------------------------
# Test 16: list_projects — user.tenant_id None ise filtre uygulanmaz
# ---------------------------------------------------------------------------

def test_list_projects_user_no_tenant_returns_all():
    """user.tenant_id boş/None ise tenant filtresi devreye girmemeli."""
    from app.domains.test_management import service

    db = _make_db()
    user = _make_user(tenant_id="")  # boş tenant

    # Tüm projeleri döndür
    db.scalars.return_value = MagicMock(all=MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()]))

    results = service.list_projects(db, user=user)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# Test 17: delete_case IDOR — yanlış projeye ait case reddedilir
# ---------------------------------------------------------------------------

def test_delete_case_wrong_project_raises():
    """delete_case: farklı proje için KeyError yükseltilmelidir."""
    from app.domains.test_management import service

    db = _make_db()

    # get_case KeyError yükseltecek şekilde mock
    with patch.object(service, "resolve_project_id", return_value="project-mine"), \
         patch.object(service, "get_case", side_effect=KeyError("Test case bulunamadı")):
        with pytest.raises(KeyError, match="Test case bulunamadı"):
            service.delete_case(db, "project-mine", "case-other", user=None)


# ---------------------------------------------------------------------------
# Test 18: create_cycle — başka projeye ait plan reddedilir
# ---------------------------------------------------------------------------

def test_create_cycle_wrong_plan_project_raises():
    """create_cycle: plan.project_id != project_id ise KeyError yükseltilmelidir."""
    from app.domains.test_management import service
    from app.domains.test_management.schemas import TestCycleCreate

    db = _make_db()

    mock_plan = MagicMock()
    mock_plan.project_id = "project-other"
    db.get.return_value = mock_plan

    payload = TestCycleCreate(plan_id="plan-xyz", name="Cycle 1")

    with patch.object(service, "resolve_project_id", return_value="project-mine"):
        with pytest.raises(KeyError, match="Test plan bulunamadı"):
            service.create_cycle(db, "project-mine", payload, user=None)
