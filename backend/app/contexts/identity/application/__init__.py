"""
Application layer — use case orchestration.

Domain'i koordine eder, infrastructure'a delegate eder.
HTTP/CLI/UI'dan bağımsız. Test edilebilir.
"""

from .register_user import RegisterUserCommand, RegisterUserHandler
from .change_email import ChangeEmailCommand, ChangeEmailHandler, UserNotFoundError, EmailConflictError
from .deactivate_user import DeactivateUserCommand, DeactivateUserHandler

__all__ = [
    "RegisterUserCommand", "RegisterUserHandler",
    "ChangeEmailCommand", "ChangeEmailHandler",
    "DeactivateUserCommand", "DeactivateUserHandler",
    "UserNotFoundError", "EmailConflictError",
]
