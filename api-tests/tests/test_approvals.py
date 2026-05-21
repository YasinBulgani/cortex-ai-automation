"""TSPM Approvals — listeleme + karar (decide) smoke testleri.

Approvals akışı otomasyonun "üretilen senaryoyu insan onayıyla ekleme"
yoludur. Şu ana kadar api-tests dizininde hiç test edilmemişti; bu dosya
contract-level minimum kaplamayı garanti eder.
"""

from __future__ import annotations

import pytest

from config.constants import FastAPIPaths


def _create_approval(api, project_id: str) -> dict:
    path = FastAPIPaths.TSPM_APPROVALS.format(project_id=project_id)
    resp = api.post(
        path,
        json={
            "source_text": "AI tarafından önerilen senaryo",
            "title": "Giriş akışı — onay bekliyor",
            "draft_payload": {
                "title": "Giriş akışı — onay bekliyor",
                "steps": [
                    {"action": "given", "text": "kullanıcı login sayfasındadır"},
                    {"action": "when", "text": "doğru kimlik bilgisi girer"},
                    {"action": "then", "text": "dashboard'a yönlendirilir"},
                ],
            },
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


@pytest.mark.smoke
class TestApprovalsCrud:
    def test_list_approvals_returns_array(self, api, project_id):
        path = FastAPIPaths.TSPM_APPROVALS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_approval_draft(self, api, project_id):
        approval = _create_approval(api, project_id)
        assert "id" in approval
        assert approval.get("title")


@pytest.mark.smoke
class TestApprovalDecide:
    def test_approve_creates_scenario(self, api, project_id):
        """Onay verince, approval bir senaryoya dönüşmeli."""
        approval = _create_approval(api, project_id)
        decide_path = FastAPIPaths.TSPM_APPROVAL_DECIDE.format(
            project_id=project_id, approval_id=approval["id"]
        )
        resp = api.post(decide_path, json={"decision": "approve"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Cevap bir scenario_id ya da güncellenmiş approval içermeli.
        assert any(k in body for k in ("scenario_id", "status", "ok", "approval"))

    def test_reject_marks_approval(self, api, project_id):
        approval = _create_approval(api, project_id)
        decide_path = FastAPIPaths.TSPM_APPROVAL_DECIDE.format(
            project_id=project_id, approval_id=approval["id"]
        )
        resp = api.post(
            decide_path,
            json={"decision": "reject", "reason": "Adımlar eksik"},
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.negative
    def test_decide_invalid_value_rejected(self, api, project_id):
        approval = _create_approval(api, project_id)
        decide_path = FastAPIPaths.TSPM_APPROVAL_DECIDE.format(
            project_id=project_id, approval_id=approval["id"]
        )
        resp = api.post(decide_path, json={"decision": "maybe"})
        assert resp.status_code in (400, 422)
