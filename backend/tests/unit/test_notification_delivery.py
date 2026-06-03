"""Notification delivery servisi testleri."""
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.services.notification_delivery import (
    send_slack_notification,
    send_teams_notification,
    send_notification,
)

# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def test_slack_notification_success():
    """Başarılı bir Slack webhook çağrısı True döndürür."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("app.services.notification_delivery.httpx.post", return_value=mock_resp) as mock_post:
        result = send_slack_notification(
            webhook_url="https://hooks.slack.com/test",
            title="Test Başlığı",
            message="Test mesajı",
        )

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.args[0] == "https://hooks.slack.com/test"


def test_slack_notification_empty_url():
    """Boş webhook_url verildiğinde httpx çağrılmadan False döner."""
    with patch("app.services.notification_delivery.httpx.post") as mock_post:
        result = send_slack_notification(
            webhook_url="",
            title="Başlık",
            message="Mesaj",
        )

    assert result is False
    mock_post.assert_not_called()


def test_slack_notification_http_error():
    """HTTP hatası (raise_for_status) durumunda exception fırlatmadan False döner."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request",
        request=MagicMock(),
        response=MagicMock(),
    )

    with patch("app.services.notification_delivery.httpx.post", return_value=mock_resp):
        result = send_slack_notification(
            webhook_url="https://hooks.slack.com/test",
            title="Başlık",
            message="Mesaj",
        )

    assert result is False


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def test_teams_notification_success():
    """Başarılı bir Teams webhook çağrısı True döndürür."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("app.services.notification_delivery.httpx.post", return_value=mock_resp) as mock_post:
        result = send_teams_notification(
            webhook_url="https://outlook.office.com/webhook/test",
            title="Teams Başlığı",
            message="Teams mesajı",
        )

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.args[0] == "https://outlook.office.com/webhook/test"


def test_teams_notification_empty_url():
    """Boş webhook_url verildiğinde httpx çağrılmadan False döner."""
    with patch("app.services.notification_delivery.httpx.post") as mock_post:
        result = send_teams_notification(
            webhook_url="",
            title="Başlık",
            message="Mesaj",
        )

    assert result is False
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# send_notification router
# ---------------------------------------------------------------------------

def test_send_notification_routes_to_slack():
    """channel='slack' olduğunda send_slack_notification çağrılır."""
    with patch(
        "app.services.notification_delivery.send_slack_notification", return_value=True
    ) as mock_slack, patch(
        "app.services.notification_delivery.send_teams_notification"
    ) as mock_teams:
        result = send_notification(
            channel="slack",
            title="Slack Başlığı",
            message="Slack mesajı",
            slack_webhook_url="https://hooks.slack.com/test",
        )

    assert result is True
    mock_slack.assert_called_once_with(
        webhook_url="https://hooks.slack.com/test",
        title="Slack Başlığı",
        message="Slack mesajı",
    )
    mock_teams.assert_not_called()


def test_send_notification_routes_to_teams():
    """channel='teams' olduğunda send_teams_notification çağrılır."""
    with patch(
        "app.services.notification_delivery.send_teams_notification", return_value=True
    ) as mock_teams, patch(
        "app.services.notification_delivery.send_slack_notification"
    ) as mock_slack:
        result = send_notification(
            channel="teams",
            title="Teams Başlığı",
            message="Teams mesajı",
            teams_webhook_url="https://outlook.office.com/webhook/test",
        )

    assert result is True
    mock_teams.assert_called_once_with(
        webhook_url="https://outlook.office.com/webhook/test",
        title="Teams Başlığı",
        message="Teams mesajı",
    )
    mock_slack.assert_not_called()


def test_send_notification_unknown_channel():
    """Bilinmeyen channel değerinde False döner, hiçbir delivery fonksiyonu çağrılmaz."""
    with patch(
        "app.services.notification_delivery.send_slack_notification"
    ) as mock_slack, patch(
        "app.services.notification_delivery.send_teams_notification"
    ) as mock_teams:
        result = send_notification(
            channel="email",
            title="Başlık",
            message="Mesaj",
        )

    assert result is False
    mock_slack.assert_not_called()
    mock_teams.assert_not_called()
