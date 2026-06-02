"""Notifications domain — real-time WebSocket notifications.

.. deprecated:: 2026-05-28
    This domain is superseded by ``app.domains.test_management`` which
    provides the persistent ``MgmtNotification`` inbox, SSE delivery, and
    multi-channel routing (in_app / email / push / slack / teams).

    The existing WebSocket-based endpoints under this package are kept
    online during the migration window — see CHANGELOG for the planned
    removal date (2026-Q4).

    Callers should migrate to:
      - ``app.domains.test_management.comments_service.emit_notification`` for
        emitting notifications from server-side code.
      - ``/api/v1/test-management/notifications/*`` for HTTP/SSE clients.
"""

import warnings as _warnings

_warnings.warn(
    "app.domains.notifications is deprecated; "
    "use app.domains.test_management.MgmtNotification (planned removal: 2026-Q4).",
    DeprecationWarning,
    stacklevel=2,
)
