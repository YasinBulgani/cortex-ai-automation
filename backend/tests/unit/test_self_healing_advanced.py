"""Self-healing retry, rollback ve bildirim testleri."""
from __future__ import annotations

import pytest
from typing import Optional
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class RetryExhausted(Exception):
    """Raised when max retries are reached."""


def open_pr(github_client, title: str, branch: str, base: str = "main"):
    """Thin wrapper that delegates to github_client.create_pull_request."""
    return github_client.create_pull_request(title=title, branch=branch, base=base)


def close_pr(github_client, pr_number: int):
    """Close (and optionally delete the head branch of) a pull request."""
    response = github_client.close_pull_request(pr_number=pr_number)
    if response is None:
        # 404 — PR not found, treat as graceful no-op
        return {"status": "not_found"}
    return response


def delete_branch(github_client, branch: str):
    """Delete a remote branch via the github client."""
    return github_client.delete_branch(branch=branch)


def notify_slack(webhook_url: Optional[str], message: str):
    """Send a Slack notification if a webhook URL is configured."""
    import requests  # noqa: PLC0415

    if not webhook_url:
        return None
    return requests.post(webhook_url, json={"text": message})


def healing_with_retry(
    action,
    *,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    sleep_fn=None,
):
    """
    Run *action* with exponential-backoff retries.

    Parameters
    ----------
    action:
        Zero-argument callable that may raise an exception.
    max_retries:
        Maximum number of attempts (including the first one).
    backoff_base:
        Initial sleep duration in seconds; doubles on each retry.
    sleep_fn:
        Optional replacement for ``time.sleep`` (injected for testing).
    """
    import time  # noqa: PLC0415

    _sleep = sleep_fn or time.sleep
    last_exc = None
    delay = backoff_base

    for attempt in range(1, max_retries + 1):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_retries:
                _sleep(delay)
                delay *= 2

    raise RetryExhausted(f"Action failed after {max_retries} attempts") from last_exc


def heal(
    github_client,
    *,
    title: str,
    branch: str,
    base: str = "main",
    slack_webhook: Optional[str] = None,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    sleep_fn=None,
):
    """
    Orchestrate: open PR with retry → notify Slack on success or failure.
    """
    try:
        result = healing_with_retry(
            lambda: open_pr(github_client, title=title, branch=branch, base=base),
            max_retries=max_retries,
            backoff_base=backoff_base,
            sleep_fn=sleep_fn,
        )
        notify_slack(slack_webhook, f"Healing succeeded: PR '{title}' opened.")
        return {"status": "success", "pr": result}
    except RetryExhausted:
        notify_slack(slack_webhook, f"Healing failed: could not open PR '{title}'.")
        return {"status": "failed"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealingRetry:
    """Retry logic for the healing action."""

    def test_healing_retry_on_pr_failed(self):
        """PR açma başarısız olunca retry yapıyor."""
        mock_client = MagicMock()
        # First call fails, second succeeds
        mock_client.create_pull_request.side_effect = [
            RuntimeError("API timeout"),
            {"number": 42, "url": "https://github.com/org/repo/pull/42"},
        ]

        sleep_mock = MagicMock()
        result = heal(
            mock_client,
            title="fix: self-healing patch",
            branch="fix/healing-branch",
            max_retries=3,
            backoff_base=1.0,
            sleep_fn=sleep_mock,
        )

        assert result["status"] == "success"
        assert result["pr"]["number"] == 42
        assert mock_client.create_pull_request.call_count == 2
        # Sleep was called exactly once (between attempt 1 and 2)
        sleep_mock.assert_called_once_with(1.0)

    def test_healing_retry_max_attempts(self):
        """max_retries'e ulaşınca durur."""
        mock_client = MagicMock()
        mock_client.create_pull_request.side_effect = RuntimeError("permanent failure")

        sleep_mock = MagicMock()
        result = heal(
            mock_client,
            title="fix: will always fail",
            branch="fix/bad-branch",
            max_retries=3,
            backoff_base=1.0,
            sleep_fn=sleep_mock,
        )

        assert result["status"] == "failed"
        # Exactly max_retries attempts
        assert mock_client.create_pull_request.call_count == 3
        # Sleep called max_retries - 1 times
        assert sleep_mock.call_count == 2

    def test_healing_retry_exponential_backoff(self):
        """Gecikme katlanarak artıyor."""
        mock_client = MagicMock()
        mock_client.create_pull_request.side_effect = RuntimeError("boom")

        sleep_mock = MagicMock()
        healing_with_retry(
            lambda: open_pr(mock_client, title="t", branch="b"),
            max_retries=4,
            backoff_base=2.0,
            sleep_fn=sleep_mock,
        ) if False else None  # We call directly below to catch RetryExhausted

        with pytest.raises(RetryExhausted):
            healing_with_retry(
                lambda: open_pr(mock_client, title="t", branch="b"),
                max_retries=4,
                backoff_base=2.0,
                sleep_fn=sleep_mock,
            )

        # Expected sleep durations: 2.0, 4.0, 8.0  (3 sleeps for 4 attempts)
        expected_calls = [call(2.0), call(4.0), call(8.0)]
        sleep_mock.assert_has_calls(expected_calls)
        assert sleep_mock.call_count == 3

    def test_healing_success_no_retry(self):
        """Başarılıysa retry yapılmıyor."""
        mock_client = MagicMock()
        mock_client.create_pull_request.return_value = {
            "number": 7,
            "url": "https://github.com/org/repo/pull/7",
        }

        sleep_mock = MagicMock()
        result = heal(
            mock_client,
            title="feat: instant success",
            branch="feat/quick",
            max_retries=3,
            backoff_base=1.0,
            sleep_fn=sleep_mock,
        )

        assert result["status"] == "success"
        assert mock_client.create_pull_request.call_count == 1
        sleep_mock.assert_not_called()


class TestGitHubRollback:
    """Rollback helpers: close PR and delete branch."""

    def test_github_close_pr_success(self):
        """PR kapatma başarılı."""
        mock_client = MagicMock()
        mock_client.close_pull_request.return_value = {"number": 42, "state": "closed"}

        result = close_pr(mock_client, pr_number=42)

        mock_client.close_pull_request.assert_called_once_with(pr_number=42)
        assert result["state"] == "closed"
        assert result["number"] == 42

    def test_github_close_pr_not_found(self):
        """404 durumunda graceful fail."""
        mock_client = MagicMock()
        # Simulate a 404: client returns None
        mock_client.close_pull_request.return_value = None

        result = close_pr(mock_client, pr_number=9999)

        mock_client.close_pull_request.assert_called_once_with(pr_number=9999)
        assert result == {"status": "not_found"}

    def test_github_delete_branch(self):
        """Branch silme."""
        mock_client = MagicMock()
        mock_client.delete_branch.return_value = {"ref": "refs/heads/fix/old-branch", "deleted": True}

        result = delete_branch(mock_client, branch="fix/old-branch")

        mock_client.delete_branch.assert_called_once_with(branch="fix/old-branch")
        assert result["deleted"] is True
        assert "fix/old-branch" in result["ref"]


class TestSlackNotifications:
    """Slack webhook notification behaviour."""

    def test_healing_notify_slack_on_success(self):
        """Başarılıda Slack bildirimi."""
        mock_client = MagicMock()
        mock_client.create_pull_request.return_value = {"number": 1}

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            heal(
                mock_client,
                title="fix: success case",
                branch="fix/success",
                slack_webhook="https://hooks.slack.com/test",
                sleep_fn=MagicMock(),
            )

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert "succeeded" in payload["text"].lower()
        assert "fix: success case" in payload["text"]

    def test_healing_notify_slack_on_failure(self):
        """Başarısızda Slack bildirimi."""
        mock_client = MagicMock()
        mock_client.create_pull_request.side_effect = RuntimeError("always fails")

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = heal(
                mock_client,
                title="fix: failure case",
                branch="fix/failure",
                slack_webhook="https://hooks.slack.com/test",
                max_retries=2,
                sleep_fn=MagicMock(),
            )

        assert result["status"] == "failed"
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert "failed" in payload["text"].lower()
        assert "fix: failure case" in payload["text"]

    def test_healing_notify_skipped_if_no_webhook(self):
        """Webhook URL yoksa bildirim atlanır."""
        mock_client = MagicMock()
        mock_client.create_pull_request.return_value = {"number": 3}

        with patch("requests.post") as mock_post:
            heal(
                mock_client,
                title="fix: no webhook",
                branch="fix/no-webhook",
                slack_webhook=None,
                sleep_fn=MagicMock(),
            )

        mock_post.assert_not_called()
