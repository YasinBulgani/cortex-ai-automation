"""TSPM Integrations CRUD + sync/stub contract tests.

Sync uygulaması henüz gerçek provider'larla (Jira, Slack, n8n) entegre
değil; ancak backend bu durumu açıkça `stub=true` bayrağıyla bildirmeli.
Bu test modülü sözleşmenin (contract) değişmemesini garanti eder:

  * UI/CI istemcileri `stub:true` görünce "bekleyen özellik" rozetiyle
    kullanıcıyı uyaracak.
  * Gerçek provider akışı eklendiğinde `stub=false` dönecek — bu test o
    zaman başarısız olup implementasyonu farkındalığa çıkaracak.
"""

from __future__ import annotations

import pytest

from config.constants import FastAPIPaths


@pytest.mark.smoke
class TestIntegrationsCrud:
    def test_list_integrations_returns_array(self, api, project_id):
        path = FastAPIPaths.TSPM_INTEGRATIONS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_integration_minimal(self, api, project_id):
        path = FastAPIPaths.TSPM_INTEGRATIONS.format(project_id=project_id)
        resp = api.post(
            path,
            json={
                "provider": "slack",
                "config": {"webhook_url": "https://hooks.slack.test/fake"},
                "is_active": True,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["provider"] == "slack"
        assert data["is_active"] is True

    @pytest.mark.negative
    def test_create_integration_missing_provider(self, api, project_id):
        path = FastAPIPaths.TSPM_INTEGRATIONS.format(project_id=project_id)
        resp = api.post(path, json={"config": {}})
        assert resp.status_code == 422


@pytest.mark.smoke
class TestIntegrationSyncStubContract:
    """Integration sync henüz stub; sözleşmeyi koruduğumuzu garanti edelim."""

    def test_sync_returns_stub_flag(self, api, project_id):
        list_path = FastAPIPaths.TSPM_INTEGRATIONS.format(project_id=project_id)
        created = api.post(
            list_path,
            json={
                "provider": "slack",
                "config": {"webhook_url": "https://hooks.slack.test/fake"},
                "is_active": True,
            },
        ).json()

        sync_path = FastAPIPaths.TSPM_INTEGRATION_SYNC.format(
            project_id=project_id, integration_id=created["id"]
        )
        resp = api.post(sync_path)
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Sözleşme: stub=true + synced_count=0 + provider alanı set.
        assert body.get("stub") is True, (
            "Sync hâlâ stub — `stub:true` bayrağı mutlaka dönmeli. "
            "Gerçek provider akışı eklendiğinde bu testi güncelleyin."
        )
        assert body.get("synced_count") == 0
        assert body.get("provider") == "slack"
        # Kullanıcıya yansıyan mesaj açıklayıcı olmalı (sessiz başarı değil).
        assert body.get("message"), "Stub sync için kullanıcı mesajı boş olmamalı"
