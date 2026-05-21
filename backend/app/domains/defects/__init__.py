"""Defect feedback loop — failed test → ticket → fix merged → re-run → verify → close.

Auto-listens to:
  execution.failed       → open_defect_from_execution()
  scenario.rerun.passed  → auto_close_if_open()

Auto-publishes:
  defect.opened
  defect.fix.requested
  defect.verified
  defect.closed
"""
from app.domains.defects.service import (
    DefectTicket,
    open_defect_from_execution,
    mark_fix_merged,
    verify_and_close,
    list_defects,
    get_defect,
    clear,
    install_listeners,
)

# Install event listeners on import so the loop wires automatically
try:
    install_listeners()
except Exception:
    pass

__all__ = [
    "DefectTicket",
    "open_defect_from_execution",
    "mark_fix_merged",
    "verify_and_close",
    "list_defects",
    "get_defect",
    "clear",
    "install_listeners",
]
