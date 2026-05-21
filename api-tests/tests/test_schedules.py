"""TSPM Schedule CRUD + trigger smoke tests.

Bu modül, otomasyonun zamanlayıcı yüzeyini doğrular:
  - Schedule yaratma + listeleme
  - Schedule güncelleme (is_active toggle)
  - Schedule silme
  - Manuel trigger (execution yaratılmalı)

Not: Zamanlayıcı APScheduler background job'larını kurar; bu testlerde
cron'un fiilen ateşlenmesini beklemiyoruz (wall-clock'a bağlı flake
oluştururdu). Sadece HTTP sözleşmesi + `trigger` endpoint'ini doğruluyoruz.
"""

from __future__ import annotations

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_schedule, random_scenario_title


def _create_scenario(api, project_id: str) -> str:
    """Schedule'a bağlayabileceğimiz basit bir senaryo oluşturur."""
    path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
    resp = api.post(path, json={"title": random_scenario_title()})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.smoke
@pytest.mark.scenarios  # scheduler kendi marker'ına sahip değil; smoke yeterli
class TestScheduleCrud:
    def test_list_schedules_empty_or_success(self, api, project_id):
        path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_schedule_with_scenario(self, api, project_id):
        scenario_id = _create_scenario(api, project_id)
        path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        payload = random_schedule()
        payload["scenario_ids"] = [scenario_id]
        resp = api.post(path, json=payload)
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["name"] == payload["name"]
        assert data["cron_expression"] == payload["cron_expression"]
        assert data["is_active"] is True

    @pytest.mark.negative
    def test_create_schedule_invalid_cron_rejected(self, api, project_id):
        """Cron ifadesi boş olamaz; Pydantic 422 dönmeli."""
        path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        resp = api.post(path, json={"name": "bad", "cron_expression": ""})
        assert resp.status_code == 422

    def test_update_schedule_toggle_active(self, api, project_id):
        scenario_id = _create_scenario(api, project_id)
        path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        payload = random_schedule()
        payload["scenario_ids"] = [scenario_id]
        created = api.post(path, json=payload).json()

        detail = f"{path}/{created['id']}"
        resp = api.patch(detail, json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_delete_schedule(self, api, project_id):
        scenario_id = _create_scenario(api, project_id)
        path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        payload = random_schedule()
        payload["scenario_ids"] = [scenario_id]
        created = api.post(path, json=payload).json()

        detail = f"{path}/{created['id']}"
        resp = api.delete(detail)
        assert resp.status_code in (200, 204)


@pytest.mark.smoke
class TestScheduleTrigger:
    def test_trigger_creates_execution(self, api, project_id):
        """Manuel trigger hem 2xx dönmeli hem de bir execution üretmeli.

        Bu test esasen "scheduler load bug'ı" (backend restart sonrası
        DB'deki schedule'lar APScheduler'a yüklenmiyor) için bir guard
        değildir; o hata `trigger` HTTP yolunu etkilemez. Ancak trigger
        sözleşmesinin bozulmadığını doğrular; bu da regresyon için önemli.
        """
        scenario_id = _create_scenario(api, project_id)
        list_path = FastAPIPaths.TSPM_SCHEDULES.format(project_id=project_id)
        payload = random_schedule()
        payload["scenario_ids"] = [scenario_id]
        created = api.post(list_path, json=payload).json()

        trigger_path = FastAPIPaths.TSPM_SCHEDULE_TRIGGER.format(
            project_id=project_id, schedule_id=created["id"]
        )
        resp = api.post(trigger_path)
        # Trigger endpoint bazı sürümlerde 200 bazılarında 202 döndürüyor;
        # sözleşmenin kırılmaması için aralığı geniş tutuyoruz.
        assert resp.status_code in (200, 202), resp.text
        body = resp.json()
        # Cevap ya execution_id taşır ya da {"triggered": true}/benzeri bir onay.
        assert any(k in body for k in ("execution_id", "id", "triggered", "ok"))
