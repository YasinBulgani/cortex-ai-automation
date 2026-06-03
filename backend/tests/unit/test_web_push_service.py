"""WebPushService birim testleri."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.web_push_service import WebPushService, get_web_push_service


SUBSCRIPTION = {
    "endpoint": "https://push.example.com/sub/123",
    "keys": {"p256dh": "FAKE_P256DH", "auth": "FAKE_AUTH"},
}


def _service_with_keys() -> WebPushService:
    return WebPushService(
        private_key="fake-private-key",
        public_key="fake-public-key",
        claims_email="test@example.com",
    )


def _service_no_keys() -> WebPushService:
    return WebPushService(
        private_key="",
        public_key="",
        claims_email="test@example.com",
    )


# ---------------------------------------------------------------------------
# 1. VAPID key yoksa send False döner
# ---------------------------------------------------------------------------

def test_web_push_disabled_when_no_keys():
    svc = _service_no_keys()
    assert svc._enabled is False
    result = svc.send(
        subscription_info=SUBSCRIPTION,
        title="Merhaba",
        body="Bu bir test",
    )
    assert result is False


# ---------------------------------------------------------------------------
# 2. Başarılı push gönderimi
# ---------------------------------------------------------------------------

def test_web_push_send_success():
    svc = _service_with_keys()

    mock_webpush = MagicMock()
    mock_exception_cls = MagicMock()

    with patch.dict(
        "sys.modules",
        {"pywebpush": MagicMock(webpush=mock_webpush, WebPushException=mock_exception_cls)},
    ):
        result = svc.send(
            subscription_info=SUBSCRIPTION,
            title="Test Başlık",
            body="Test gövde",
            url="/dashboard",
            tag="test-tag",
        )

    assert result is True
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"] == SUBSCRIPTION
    assert call_kwargs["vapid_private_key"] == "fake-private-key"
    assert "mailto:test@example.com" in call_kwargs["vapid_claims"]["sub"]

    import json
    payload = json.loads(call_kwargs["data"])
    assert payload["title"] == "Test Başlık"
    assert payload["body"] == "Test gövde"
    assert payload["data"]["url"] == "/dashboard"
    assert payload["tag"] == "test-tag"


# ---------------------------------------------------------------------------
# 3. pywebpush kurulu değilse graceful fail
# ---------------------------------------------------------------------------

def test_web_push_send_import_error():
    svc = _service_with_keys()

    with patch.builtins.__import__ if False else patch(
        "app.services.web_push_service.WebPushService.send",
        wraps=svc.send,
    ):
        pass  # use direct approach below

    # Simulate ImportError by patching __import__ for pywebpush
    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _fake_import(name, *args, **kwargs):
        if name == "pywebpush":
            raise ImportError("No module named 'pywebpush'")
        return original_import(name, *args, **kwargs)

    import builtins
    with patch.object(builtins, "__import__", side_effect=_fake_import):
        result = svc.send(
            subscription_info=SUBSCRIPTION,
            title="Test",
            body="Body",
        )

    assert result is False


# ---------------------------------------------------------------------------
# 4. Network hatasında False döner, exception atmaz
# ---------------------------------------------------------------------------

def test_web_push_send_network_error():
    svc = _service_with_keys()

    mock_webpush = MagicMock(side_effect=Exception("Connection refused"))
    mock_exception_cls = MagicMock()

    with patch.dict(
        "sys.modules",
        {"pywebpush": MagicMock(webpush=mock_webpush, WebPushException=mock_exception_cls)},
    ):
        result = svc.send(
            subscription_info=SUBSCRIPTION,
            title="Test",
            body="Body",
        )

    assert result is False


# ---------------------------------------------------------------------------
# 5. Bazı subscriptions başarılı bazıları değil (send_bulk partial)
# ---------------------------------------------------------------------------

def test_web_push_send_bulk_partial():
    svc = _service_with_keys()

    subscriptions = [
        {"endpoint": "https://push.example.com/sub/1", "keys": {}},
        {"endpoint": "https://push.example.com/sub/2", "keys": {}},
        {"endpoint": "https://push.example.com/sub/3", "keys": {}},
    ]

    call_count = 0

    def _alternating_send(**kwargs):
        nonlocal call_count
        call_count += 1
        # 1. ve 3. başarılı, 2. başarısız
        return call_count % 2 == 1

    with patch.object(svc, "send", side_effect=_alternating_send):
        ok, failed = svc.send_bulk(
            subscriptions=subscriptions,
            title="Toplu",
            body="Toplu gövde",
        )

    assert ok == 2
    assert failed == 1


# ---------------------------------------------------------------------------
# 6. (ok, failed) tuple doğru döner
# ---------------------------------------------------------------------------

def test_web_push_send_bulk_counts():
    svc = _service_with_keys()

    subscriptions = [
        {"endpoint": f"https://push.example.com/sub/{i}", "keys": {}}
        for i in range(5)
    ]

    with patch.object(svc, "send", return_value=True):
        ok, failed = svc.send_bulk(
            subscriptions=subscriptions,
            title="Tümü Başarılı",
            body="Gövde",
        )

    assert ok == 5
    assert failed == 0
    assert isinstance(ok, int)
    assert isinstance(failed, int)

    with patch.object(svc, "send", return_value=False):
        ok2, failed2 = svc.send_bulk(
            subscriptions=subscriptions,
            title="Tümü Başarısız",
            body="Gövde",
        )

    assert ok2 == 0
    assert failed2 == 5


# ---------------------------------------------------------------------------
# 7. get_web_push_service factory (dependency injection)
# ---------------------------------------------------------------------------

def test_get_web_push_service_factory():
    mock_settings = MagicMock()
    mock_settings.vapid_private_key = "test-private"
    mock_settings.vapid_public_key = "test-public"
    mock_settings.vapid_claims_email = "factory@example.com"

    with patch("app.config.settings", mock_settings):
        svc = get_web_push_service()

    assert isinstance(svc, WebPushService)
    assert svc.private_key == "test-private"
    assert svc.public_key == "test-public"
    assert svc.claims_email == "factory@example.com"
    assert svc._enabled is True
