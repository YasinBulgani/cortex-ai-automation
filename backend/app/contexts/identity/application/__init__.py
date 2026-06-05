"""
Application layer — use case orchestration.

Domain'i koordine eder, infrastructure'a delegate eder.
HTTP/CLI/UI'dan bağımsız. Test edilebilir.
"""

from .change_email import ChangeEmailCommand, ChangeEmailHandler, EmailConflictError, UserNotFoundError
from .deactivate_user import DeactivateUserCommand, DeactivateUserHandler
from .register_user import RegisterUserCommand, RegisterUserHandler

__all__ = [
    "RegisterUserCommand", "RegisterUserHandler",
    "ChangeEmailCommand", "ChangeEmailHandler",
    "DeactivateUserCommand", "DeactivateUserHandler",
    "UserNotFoundError", "EmailConflictError",
]
