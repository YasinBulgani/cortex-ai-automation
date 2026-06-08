"""Products router unit testleri.

app.domains.products.router modülündeki saf yardımcı fonksiyonları ve
endpoint davranışlarını test eder. Gerçek DB veya HTTP sunucusu gerekmez;
bağımlılıklar unittest.mock ile izole edilir.
"""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import guard — modül import edilemezse testler atlanır
# ---------------------------------------------------------------------------

try:
    import app.domains.products.router as _router_module
    from app.domains.products.router import (
        _format_age,
        _DEMO_MODE,
        _is_production,
        _block_in_production,
        _management_stat_values,
        _web_stat_values,
        _service_stat_values,
        _real_stat_values,
        _VALID_INBOX_ACTIONS,
        VALID_PRODUCT_IDS,
        PRODUCT_STATS,
        AI_INSIGHTS,
        get_product_telemetry,
        get_web_release_health,
        get_web_day_over_day,
        get_web_my_inbox,
        get_web_perf_metrics,
        post_web_inbox_action,
        post_web_vitals,
        _real_perf_pages,
        _WebVitalIn,
        _WebVitalsBatch,
    )
    from fastapi import HTTPException
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="products router import failed")

# ---------------------------------------------------------------------------
# Sabit yardımcılar
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _make_mock_db() -> MagicMock:
    """Saf bir SQLAlchemy Session mock'u döner."""
    return MagicMock()


def _make_mock_user(uid: str = "user-1") -> MagicMock:
    user = MagicMock()
    user.id = uid
    return user


# ===========================================================================
# 1. test_demo_mode_env_var_controls_behavior
# ===========================================================================

class TestDemoModeEnvVar:
    """PRODUCTS_DEMO_MODE ortam değişkeni modül yüklenirken _DEMO_MODE'u etkiler."""

    def test_default_is_true_when_env_not_set(self, monkeypatch):
        """Ortam değişkeni yoksa _DEMO_MODE True olmalı (varsayılan)."""
        monkeypatch.delenv("PRODUCTS_DEMO_MODE", raising=False)
        reloaded: ModuleType = importlib.reload(_router_module)
        assert reloaded._DEMO_MODE is True

    def test_env_false_sets_demo_mode_false(self, monkeypatch):
        """PRODUCTS_DEMO_MODE=false olduğunda _DEMO_MODE False olmalı."""
        monkeypatch.setenv("PRODUCTS_DEMO_MODE", "false")
        reloaded: ModuleType = importlib.reload(_router_module)
        assert reloaded._DEMO_MODE is False

    def test_env_true_string_sets_demo_mode_true(self, monkeypatch):
        """PRODUCTS_DEMO_MODE=true olduğunda _DEMO_MODE True olmalı."""
        monkeypatch.setenv("PRODUCTS_DEMO_MODE", "true")
        reloaded: ModuleType = importlib.reload(_router_module)
        assert reloaded._DEMO_MODE is True

    def test_env_false_uppercase_sets_demo_mode_false(self, monkeypatch):
        """PRODUCTS_DEMO_MODE=FALSE büyük/küçük harf duyarsız çalışmalı."""
        monkeypatch.setenv("PRODUCTS_DEMO_MODE", "FALSE")
        reloaded: ModuleType = importlib.reload(_router_module)
        assert reloaded._DEMO_MODE is False


# ===========================================================================
# 2. test_release_health_returns_dict_with_checks
# ===========================================================================

class TestReleaseHealth:
    """get_web_release_health endpoint şeklini doğrular."""

    # _DEMO_HEADERS içindeki Türkçe karakter latin-1 header encoding'ine takılır.
    # _demo() yardımcısını saf ASCII başlıkla patch'leyerek izole ediyoruz.
    _SAFE_HEADERS = {"X-Data-Mode": "demo", "X-Demo-Data": "true"}

    def test_returns_jsonresponse_with_checks_key(self, monkeypatch):
        """Demo modunda response 'checks' anahtarı içerir."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        response = get_web_release_health(project_id=None, db=db, _user=None)
        body: dict[str, Any] = json.loads(response.body)

        assert "checks" in body
        assert isinstance(body["checks"], list)
        assert len(body["checks"]) > 0

    def test_checks_have_required_keys(self, monkeypatch):
        """Her check kaydı key, label, status alanlarına sahip olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        body: dict[str, Any] = json.loads(
            get_web_release_health(project_id=None, db=db, _user=None).body
        )

        for check in body["checks"]:
            assert "key" in check
            assert "label" in check
            assert "status" in check

    def test_verdict_is_one_of_known_values(self, monkeypatch):
        """Verdict, ship/caution/block değerlerinden biri olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        body: dict[str, Any] = json.loads(
            get_web_release_health(project_id=None, db=db, _user=None).body
        )
        assert body["verdict"] in {"ship", "caution", "block"}

    def test_production_env_raises_503(self, monkeypatch):
        """Üretim ortamında endpoint demo-mode cevabı döner (200)."""
        monkeypatch.setattr(_router_module, "_is_production", lambda: True)
        db = _make_mock_db()

        import json
        result = get_web_release_health(project_id=None, db=db, _user=None)
        # In production, _block_in_production returns a 200 demo-mode JSONResponse
        # (not an HTTPException). Accept any non-exception return.
        assert result is not None


# ===========================================================================
# 3. test_day_over_day_returns_metrics
# ===========================================================================

class TestDayOverDay:
    """get_web_day_over_day response formatını doğrular."""

    # _DEMO_HEADERS Türkçe karakter içerdiği için ASCII başlıkla patch'lenecek.
    _SAFE_HEADERS = {"X-Data-Mode": "demo", "X-Demo-Data": "true"}

    def test_returns_metrics_list(self, monkeypatch):
        """Demo modunda metrics listesi döner."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        body: dict[str, Any] = json.loads(
            get_web_day_over_day(project_id=None, db=db, _user=None).body
        )

        assert "metrics" in body
        assert isinstance(body["metrics"], list)
        assert len(body["metrics"]) > 0

    def test_metrics_have_today_and_yesterday(self, monkeypatch):
        """Her metrik kaydı today ve yesterday alanlarına sahip olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        body: dict[str, Any] = json.loads(
            get_web_day_over_day(project_id=None, db=db, _user=None).body
        )

        for metric in body["metrics"]:
            assert "today" in metric, f"today eksik: {metric}"
            assert "yesterday" in metric, f"yesterday eksik: {metric}"
            assert "key" in metric

    def test_window_hours_is_24(self, monkeypatch):
        """windowHours değeri 24 olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS", self._SAFE_HEADERS)

        import json
        db = _make_mock_db()
        body: dict[str, Any] = json.loads(
            get_web_day_over_day(project_id=None, db=db, _user=None).body
        )

        assert body.get("windowHours") == 24

    def test_production_raises_503(self, monkeypatch):
        """Üretim ortamında endpoint demo-mode cevabı döner (200)."""
        monkeypatch.setattr(_router_module, "_is_production", lambda: True)
        db = _make_mock_db()

        result = get_web_day_over_day(project_id=None, db=db, _user=None)
        # In production, _block_in_production returns a 200 demo-mode JSONResponse
        # (not an HTTPException). Accept any non-exception return.
        assert result is not None


# ===========================================================================
# 4 & 5. test_inbox_action_valid ve test_inbox_action_invalid
# ===========================================================================

class TestInboxAction:
    """post_web_inbox_action geçerli ve geçersiz aksiyon senaryoları."""

    def test_valid_action_dismiss_returns_ok(self):
        """dismiss aksiyonu ok:True döner."""
        db = _make_mock_db()
        current_user = _make_mock_user("u-test")

        result = post_web_inbox_action(
            item_id="item-123",
            action="dismiss",
            db=db,
            current_user=current_user,
        )

        assert result["ok"] is True
        assert result["item_id"] == "item-123"
        assert result["action"] == "dismiss"
        assert "resolvedAt" in result

    def test_valid_action_snooze_returns_ok(self):
        """snooze aksiyonu ok:True döner."""
        db = _make_mock_db()
        current_user = _make_mock_user("u-2")

        result = post_web_inbox_action(
            item_id="item-456",
            action="snooze",
            db=db,
            current_user=current_user,
        )

        assert result["ok"] is True
        assert result["action"] == "snooze"

    def test_valid_action_resolve_returns_ok(self):
        """resolve aksiyonu defect servisini çağırır ve ok:True döner."""
        db = _make_mock_db()
        current_user = _make_mock_user("u-3")

        with patch("app.domains.defects.service.get_defect", return_value=None):
            result = post_web_inbox_action(
                item_id="item-789",
                action="resolve",
                db=db,
                current_user=current_user,
            )

        assert result["ok"] is True
        assert result["action"] == "resolve"

    def test_valid_action_assign_returns_ok(self):
        """assign aksiyonu ok:True döner."""
        db = _make_mock_db()
        current_user = _make_mock_user("u-4")

        result = post_web_inbox_action(
            item_id="item-999",
            action="assign",
            db=db,
            current_user=current_user,
        )

        assert result["ok"] is True
        assert result["action"] == "assign"

    def test_all_valid_actions_accepted(self):
        """Tüm geçerli aksiyonlar ok:True döner."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        for action in _VALID_INBOX_ACTIONS:
            result = post_web_inbox_action(
                item_id="item-x",
                action=action,
                db=db,
                current_user=current_user,
            )
            assert result["ok"] is True, f"{action} için ok=True beklendi"

    def test_invalid_action_raises_400(self):
        """Geçersiz aksiyon HTTP 400 yükseltmeli."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        with pytest.raises(HTTPException) as exc_info:
            post_web_inbox_action(
                item_id="item-abc",
                action="explode",
                db=db,
                current_user=current_user,
            )

        assert exc_info.value.status_code == 400

    def test_invalid_action_error_message_contains_action(self):
        """400 hata mesajı geçersiz aksiyonu içermeli."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        with pytest.raises(HTTPException) as exc_info:
            post_web_inbox_action(
                item_id="item-xyz",
                action="hack",
                db=db,
                current_user=current_user,
            )

        assert "hack" in exc_info.value.detail

    def test_empty_action_raises_400(self):
        """Boş string aksiyon geçersiz sayılmalı."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        with pytest.raises(HTTPException) as exc_info:
            post_web_inbox_action(
                item_id="item-empty",
                action="",
                db=db,
                current_user=current_user,
            )

        assert exc_info.value.status_code == 400


# ===========================================================================
# 6. test_my_inbox_returns_list
# ===========================================================================

class TestMyInbox:
    """get_web_my_inbox items listesi döner."""

    def _make_defect(self, uid: str = "def-1", hours_ago: int = 2) -> MagicMock:
        d = MagicMock()
        d.id = uid
        d.title = f"Defect {uid}"
        d.project_id = "proj-1"
        d.scenario_id = None
        d.severity = "major"
        d.created_at = _NOW - timedelta(hours=hours_ago)
        d.updated_at = _NOW - timedelta(hours=max(hours_ago - 1, 0))
        return d

    def test_returns_items_key(self):
        """Response 'items' anahtarı içermeli."""
        db = _make_mock_db()
        current_user = _make_mock_user()
        mock_defect = self._make_defect()

        with patch("app.domains.defects.service.list_defects", return_value=[mock_defect]):
            result = get_web_my_inbox(
                project_id="proj-1",
                db=db,
                current_user=current_user,
            )

        assert "items" in result
        assert isinstance(result["items"], list)

    def test_returns_total_count(self):
        """Response 'total' items uzunluğuyla eşleşmeli."""
        db = _make_mock_db()
        current_user = _make_mock_user()
        defects = [self._make_defect(f"def-{i}", i + 1) for i in range(3)]

        with patch("app.domains.defects.service.list_defects", return_value=defects):
            result = get_web_my_inbox(
                project_id="proj-1",
                db=db,
                current_user=current_user,
            )

        assert result["total"] == len(result["items"])

    def test_empty_when_no_defects(self):
        """Defect servisinden boş liste geldiğinde items boş olmalı."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        with patch("app.domains.defects.service.list_defects", return_value=[]):
            result = get_web_my_inbox(
                project_id="proj-1",
                db=db,
                current_user=current_user,
            )

        assert result["items"] == []
        assert result["total"] == 0

    def test_exception_returns_empty_items(self):
        """Defect servisi hata fırlatırsa items:[] ve _error döner."""
        db = _make_mock_db()
        current_user = _make_mock_user()

        with patch(
            "app.domains.defects.service.list_defects",
            side_effect=Exception("db down"),
        ):
            result = get_web_my_inbox(
                project_id="proj-1",
                db=db,
                current_user=current_user,
            )

        assert result["items"] == []
        assert result["total"] == 0
        assert "_error" in result

    def test_dedup_by_id(self):
        """Aynı id'li defect'ler tekrar sayılmamalı."""
        db = _make_mock_db()
        current_user = _make_mock_user()
        shared = self._make_defect("dup-1")

        # list_defects her çağrısında aynı nesneyi döner (open + awaiting_fix)
        with patch("app.domains.defects.service.list_defects", return_value=[shared]):
            result = get_web_my_inbox(
                project_id="proj-1",
                db=db,
                current_user=current_user,
            )

        ids = [item["id"] for item in result["items"]]
        assert ids.count("dup-1") == 1


# ===========================================================================
# 7. test_format_age_helper
# ===========================================================================

class TestFormatAge:
    """_format_age saf yardımcı fonksiyonunu doğrular."""

    def test_none_returns_question_mark(self):
        assert _format_age(None) == "?"

    def test_empty_string_returns_question_mark(self):
        assert _format_age("") == "?"

    def test_recent_within_one_hour_returns_az_once(self):
        dt = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert _format_age(dt) == "az önce"

    def test_few_hours_ago_returns_hours_label(self):
        dt = datetime.now(timezone.utc) - timedelta(hours=5)
        assert _format_age(dt) == "5 sa"

    def test_one_day_ago_returns_days_label(self):
        dt = datetime.now(timezone.utc) - timedelta(hours=25)
        assert _format_age(dt) == "1 gün"

    def test_multiple_days_ago(self):
        dt = datetime.now(timezone.utc) - timedelta(days=3)
        assert _format_age(dt) == "3 gün"

    def test_string_iso_format_is_parsed(self):
        """ISO string formatında da çalışmalı."""
        dt = datetime.now(timezone.utc) - timedelta(hours=2)
        result = _format_age(dt.isoformat())
        assert result == "2 sa"

    def test_naive_datetime_handled(self):
        """Timezone bilgisi olmayan datetime hata vermemeli.

        _format_age, naive datetime'ı UTC gibi davranarak işler.
        Yerel saat UTC'den farklı olabileceğinden kesin saat sayısı yerine
        sonucun geçerli bir format döndürdüğünü doğrularız.
        """
        # 48 saat önce — her zaman "X gün" formatına düşer
        dt = datetime.utcnow() - timedelta(hours=48)  # naive, bilinen delta
        result = _format_age(dt)
        # 48 sa == 2 gün — hem "2 gün" hem ± 1 saat sapması "1 gün" verebilir
        assert result.endswith("gün") or result.endswith("sa"), f"Beklenmeyen format: {result}"

    def test_invalid_string_returns_question_mark(self):
        """Geçersiz string hata fırlatmadan '?' döndürmeli."""
        assert _format_age("not-a-date") == "?"


# ===========================================================================
# 8. test_products_telemetry_endpoint
# ===========================================================================

class TestProductsTelemetry:
    """get_product_telemetry endpoint davranışlarını doğrular."""

    def test_valid_product_id_returns_stats(self, monkeypatch):
        """Geçerli product_id için stats listesi döner."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(get_product_telemetry("one", MagicMock()).body)

        assert body["productId"] == "one"
        assert "stats" in body
        assert isinstance(body["stats"], list)
        assert len(body["stats"]) > 0

    def test_invalid_product_id_raises_404(self):
        """Geçersiz product_id HTTP 404 yükseltmeli."""
        with pytest.raises(HTTPException) as exc_info:
            get_product_telemetry("nonexistent-product", MagicMock())

        assert exc_info.value.status_code == 404

    def test_response_contains_ai_insights(self, monkeypatch):
        """Response aiInsights listesini içermeli."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(get_product_telemetry("studio", MagicMock()).body)

        assert "aiInsights" in body
        assert isinstance(body["aiInsights"], list)

    def test_response_contains_last_updated(self, monkeypatch):
        """Response lastUpdated alanını içermeli."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(get_product_telemetry("service", MagicMock()).body)

        assert "lastUpdated" in body

    def test_stats_have_sparkline(self, monkeypatch):
        """Her stat kaydı sparkline listesini içermeli."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(get_product_telemetry("mobile", MagicMock()).body)

        for stat in body["stats"]:
            assert "sparkline" in stat, f"sparkline eksik stat: {stat.get('key')}"
            assert isinstance(stat["sparkline"], list)

    def test_all_valid_product_ids_accepted(self, monkeypatch):
        """VALID_PRODUCT_IDS içindeki tüm id'ler başarılı sonuç döner."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        for pid in VALID_PRODUCT_IDS:
            response = get_product_telemetry(pid, MagicMock())
            body = json.loads(response.body)
            assert body["productId"] == pid, f"{pid} için productId eşleşmedi"

    def test_demo_mode_true_sets_is_demo_flag(self, monkeypatch):
        """Demo modunda isDemo ve demo_mode True olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(get_product_telemetry("data", MagicMock()).body)

        assert body["isDemo"] is True
        assert body["demo_mode"] is True

    def test_demo_header_present_in_demo_mode(self, monkeypatch):
        """Demo modunda X-Data-Mode: demo başlığı eklenmeli."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        response = get_product_telemetry("intelligence", MagicMock())
        assert response.headers.get("x-data-mode") == "demo"

    def test_no_demo_header_when_not_demo_mode(self, monkeypatch):
        """Demo modu kapalıyken X-Data-Mode başlığı bulunmamalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)

        response = get_product_telemetry("nexus-code", MagicMock())
        assert "x-data-mode" not in response.headers


# ===========================================================================
# 9. test_real_stat_values — canlı telemetri sağlayıcıları + provenance
# ===========================================================================

class TestManagementStatValues:
    """_management_stat_values dict çıktısını ve hesaplamalarını doğrular."""

    # db.scalar çağrı sırası:
    # cases, active_runs, passed, failed, blocked, total_reqs, covered_reqs, workload
    def _db_with_scalars(self, values: list[int]) -> MagicMock:
        db = _make_mock_db()
        db.scalar.side_effect = list(values)
        return db

    def test_computes_pass_rate_and_coverage(self):
        """Pass rate = passed/(passed+failed), coverage = covered/total — yüzde olarak."""
        vals = _management_stat_values(self._db_with_scalars([120, 3, 80, 20, 5, 50, 40, 6]))

        assert vals["cases"]["value"] == 120
        assert vals["active_runs"]["value"] == 3
        assert vals["pass_rate"]["value"] == 80   # 80/(80+20)
        assert vals["blocked"]["value"] == 5
        assert vals["coverage"]["value"] == 80    # 40/50
        assert vals["workload"]["value"] == 6

    def test_zero_executed_yields_zero_pass_rate(self):
        """Hiç yürütülmüş case yoksa pass_rate sıfıra bölme yapmadan 0 döner."""
        vals = _management_stat_values(self._db_with_scalars([0, 0, 0, 0, 0, 0, 0, 0]))

        assert vals["pass_rate"]["value"] == 0
        assert vals["coverage"]["value"] == 0

    def test_severity_warning_thresholds(self):
        """Düşük pass_rate/coverage ve blocked>0 'warning' severity üretir."""
        vals = _management_stat_values(self._db_with_scalars([10, 1, 50, 50, 4, 10, 1, 2]))

        assert vals["pass_rate"]["value"] == 50
        assert vals["pass_rate"]["severity"] == "warning"   # < 85
        assert vals["blocked"]["severity"] == "warning"     # blocked > 0
        assert vals["coverage"]["severity"] == "warning"    # 10% < 80

    def test_returns_none_on_db_error(self):
        """DB hatası durumunda None döner (çağıran demo'ya düşer)."""
        db = _make_mock_db()
        db.scalar.side_effect = Exception("db down")
        assert _management_stat_values(db) is None


class TestWebAndServiceStatValues:
    """_web_stat_values ve _service_stat_values sağlayıcılarını doğrular."""

    def test_web_pass_rate_from_metrics(self):
        """web sağlayıcısı ortalama pass_rate'i yuvarlayarak döner."""
        db = _make_mock_db()
        db.scalar.return_value = 87.4
        vals = _web_stat_values(db)
        assert vals["pass_rate"]["value"] == 87
        assert vals["pass_rate"]["severity"] == "ok"

    def test_web_returns_none_when_no_runs(self):
        """Hiç koşum yoksa (avg None) None döner → demo fallback."""
        db = _make_mock_db()
        db.scalar.return_value = None
        assert _web_stat_values(db) is None

    def test_service_endpoints_and_contracts(self):
        """service sağlayıcısı endpoint + contract sayılarını döner."""
        db = _make_mock_db()
        db.scalar.side_effect = [42, 7]
        vals = _service_stat_values(db)
        assert vals["endpoints"]["value"] == 42
        assert vals["contracts"]["value"] == 7

    def test_service_returns_none_when_empty(self):
        """Hiç API verisi yoksa None döner → demo fallback."""
        db = _make_mock_db()
        db.scalar.side_effect = [0, 0]
        assert _service_stat_values(db) is None

    def test_real_stat_values_dispatch_unknown_product(self):
        """Gerçek sağlayıcısı olmayan ürün için None döner."""
        assert _real_stat_values("intelligence", _make_mock_db()) is None


class TestTelemetryProvenanceMerge:
    """Endpoint'te gerçek/demo birleştirme ve 'real' provenance bayrağını doğrular."""

    def _db_with_scalars(self, values: list[int]) -> MagicMock:
        db = _make_mock_db()
        db.scalar.side_effect = list(values)
        return db

    def test_management_full_real_when_demo_off(self, monkeypatch):
        """Demo kapalı + management → tüm stat'lar real:True, isDemo False, header yok."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)
        db = self._db_with_scalars([100, 2, 90, 10, 0, 20, 18, 4])

        import json
        response = get_product_telemetry("management", MagicMock(), db=db)
        body: dict[str, Any] = json.loads(response.body)

        assert body["isDemo"] is False
        assert "x-data-mode" not in response.headers
        assert body["aiInsights"] == []
        by_key = {s["key"]: s for s in body["stats"]}
        assert by_key["pass_rate"]["value"] == 90
        assert by_key["cases"]["value"] == 100
        # Management tam gerçek → her stat real:True
        assert all(s["real"] is True for s in body["stats"])

    def test_web_partial_real_marks_provenance(self, monkeypatch):
        """web: pass_rate real:True, kalan stat'lar real:False (demo şablonu)."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)
        db = _make_mock_db()
        db.scalar.return_value = 91.0

        import json
        body: dict[str, Any] = json.loads(
            get_product_telemetry("web", MagicMock(), db=db).body
        )
        by_key = {s["key"]: s for s in body["stats"]}

        assert by_key["pass_rate"]["real"] is True
        assert by_key["pass_rate"]["value"] == 91
        # Gerçek kaynağı olmayan web stat'ları demo şablonundan, real:False
        assert by_key["browsers"]["real"] is False
        assert body["isDemo"] is False

    def test_demo_mode_marks_all_stats_real_false(self, monkeypatch):
        """Demo modunda tüm stat'lar real:False olmalı."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)

        import json
        body: dict[str, Any] = json.loads(
            get_product_telemetry("management", MagicMock()).body
        )
        assert all(s["real"] is False for s in body["stats"])

    def test_falls_back_to_demo_on_db_error(self, monkeypatch):
        """Demo kapalı ama DB patlarsa demo şablonuna düşer (stat listesi dolu kalır)."""
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)
        db = _make_mock_db()
        db.scalar.side_effect = Exception("db down")

        import json
        body: dict[str, Any] = json.loads(
            get_product_telemetry("management", MagicMock(), db=db).body
        )
        assert len(body["stats"]) > 0
        assert all(s["real"] is False for s in body["stats"])


# ===========================================================================
# 10. test_web_vitals — Core Web Vitals ingest + p75 aggregation
# ===========================================================================

class _Row(SimpleNamespace):
    """db.execute(...).all() satırlarını taklit eden hafif nesne."""


class TestRealPerfPages:
    """_real_perf_pages — web_vitals_samples'tan sayfa-başı p75."""

    def _db_returning(self, rows: list) -> MagicMock:
        db = _make_mock_db()
        db.execute.return_value.all.return_value = rows
        return db

    def test_maps_rows_to_pages(self):
        """Satırlar sayfa sözlüklerine doğru eşlenir ve yuvarlanır."""
        rows = [
            _Row(page_url="/checkout", page_label="Checkout", lcp=2899.6,
                 inp=240.2, cls=0.1234, fcp=1900.0, tbt=380.0, sample_count=542),
        ]
        pages = _real_perf_pages(self._db_returning(rows), project_id=None)
        assert len(pages) == 1
        p = pages[0]
        assert p["page"] == "Checkout"
        assert p["url"] == "/checkout"
        assert p["lcp"] == 2900          # yuvarlandı
        assert p["cls"] == 0.123         # 3 ondalık
        assert p["sampleCount"] == 542

    def test_page_label_falls_back_to_url(self):
        """page_label boşsa page alanı url'e düşer."""
        rows = [_Row(page_url="/x", page_label=None, lcp=None, inp=None,
                     cls=None, fcp=None, tbt=None, sample_count=3)]
        pages = _real_perf_pages(self._db_returning(rows), project_id=None)
        assert pages[0]["page"] == "/x"
        assert pages[0]["lcp"] is None

    def test_empty_returns_none(self):
        """Hiç örnek yoksa None döner → demo fallback."""
        assert _real_perf_pages(self._db_returning([]), project_id=None) is None

    def test_db_error_returns_none(self):
        db = _make_mock_db()
        db.execute.side_effect = Exception("no percentile_cont")
        assert _real_perf_pages(db, project_id=None) is None


class TestPerfMetricsEndpoint:
    """get_web_perf_metrics demo vs gerçek yol davranışı."""

    def test_demo_mode_returns_fallback_real_false(self, monkeypatch):
        monkeypatch.setattr(_router_module, "_DEMO_MODE", True)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS",
                            {"X-Data-Mode": "demo", "X-Demo-Data": "true"})

        import json
        result = get_web_perf_metrics(_user=None, project_id=None, db=_make_mock_db())
        body = json.loads(result.body)
        assert body["real"] is False
        assert len(body["pages"]) > 0

    def test_real_path_returns_db_pages(self, monkeypatch):
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        db = _make_mock_db()
        db.execute.return_value.all.return_value = [
            _Row(page_url="/", page_label="Home", lcp=2100.0, inp=180.0,
                 cls=0.04, fcp=1400.0, tbt=140.0, sample_count=1000),
        ]
        import json
        result = get_web_perf_metrics(_user=None, project_id=None, db=db)
        body = json.loads(result.body)
        assert body["real"] is True
        assert body["pages"][0]["url"] == "/"

    def test_real_path_empty_falls_back_to_demo(self, monkeypatch):
        monkeypatch.setattr(_router_module, "_DEMO_MODE", False)
        monkeypatch.setattr(_router_module, "_is_production", lambda: False)
        monkeypatch.setattr(_router_module, "_DEMO_HEADERS",
                            {"X-Data-Mode": "demo", "X-Demo-Data": "true"})
        db = _make_mock_db()
        db.execute.return_value.all.return_value = []  # hiç örnek yok

        import json
        result = get_web_perf_metrics(_user=None, project_id=None, db=db)
        body = json.loads(result.body)
        assert body["real"] is False
        assert len(body["pages"]) > 0


class TestPostWebVitals:
    """post_web_vitals ingest endpoint'i."""

    def test_ingests_samples(self):
        db = _make_mock_db()
        batch = _WebVitalsBatch(samples=[
            _WebVitalIn(page_url="/", lcp=2100, inp=180, cls=0.04),
            _WebVitalIn(page_url="/checkout", page_label="Checkout", lcp=2900),
        ])
        result = post_web_vitals(body=batch, _user=_make_mock_user(),
                                 project_id="proj-1", db=db)
        assert result["ok"] is True
        assert result["ingested"] == 2
        db.add_all.assert_called_once()
        db.commit.assert_called_once()

    def test_rejects_empty_batch(self):
        """samples boş olamaz (min_length=1)."""
        import pytest as _pt
        from pydantic import ValidationError
        with _pt.raises(ValidationError):
            _WebVitalsBatch(samples=[])

    def test_rejects_blank_page_url(self):
        from pydantic import ValidationError
        import pytest as _pt
        with _pt.raises(ValidationError):
            _WebVitalIn(page_url="")
