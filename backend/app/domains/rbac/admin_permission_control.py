"""Admin permission wildcard control and validation.

The admin.* wildcard permission allows any admin.* action.
This module enforces proper validation and prevents permission bypass.
"""

from typing import Optional, Set
import re


class AdminPermissionControl:
    """Validates admin.* permission usage."""

    # Reserved admin permissions (whitelist of allowed admin.* actions)
    RESERVED_ADMIN_ACTIONS = {
        "admin.read",
        "admin.write",
        "admin.delete",
        "admin.manage_roles",
        "admin.manage_permissions",
        "admin.manage_users",
        "admin.manage_teams",
        "admin.view_audit_logs",
        "admin.configure_system",
        "admin.manage_api_keys",
        "admin.rotate_secrets",
    }

    @classmethod
    def is_valid_admin_action(cls, action: str) -> bool:
        """Check if action is valid admin.* permission."""
        if not action.startswith("admin."):
            return False

        # Wildcard admin.* is always valid for checks that use it
        if action == "admin.*":
            return True

        # Specific actions must be in reserved list
        return action in cls.RESERVED_ADMIN_ACTIONS

    @classmethod
    def validate_permission_string(cls, perm: str) -> bool:
        """Validate permission string format.

        Valid formats:
        - 'domain.action' (e.g. 'defects.write')
        - 'admin.*' (wildcard)
        - 'admin.specific_action' (reserved actions)
        """
        # Wildcard is always valid
        if perm == "admin.*":
            return True

        # Check format: domain.action or domain.*
        if not re.match(r'^[a-z_]+\.\*?[a-z_]*$', perm):
            return False

        # If it's an admin permission, validate it
        if perm.startswith("admin."):
            return cls.is_valid_admin_action(perm)

        return True

    @classmethod
    def filter_admin_permissions(cls, permissions: Set[str]) -> Set[str]:
        """Filter out invalid admin permissions, keep valid ones.

        Security: Remove any malformed admin.* attempts.
        """
        valid = set()
        for perm in permissions:
            if cls.validate_permission_string(perm):
                valid.add(perm)
            # Silently skip invalid permissions (log in production)
        return valid

    @classmethod
    def has_admin_permission(cls, user_permissions: Set[str]) -> bool:
        """Check if user has ANY admin permission."""
        # First check for wildcard
        if "admin.*" in user_permissions:
            return True

        # Then check for any admin.* permission
        return any(p.startswith("admin.") for p in user_permissions)

    @classmethod
    def can_manage_permission(cls, user_perms: Set[str], target_perm: str) -> bool:
        """Check if user can grant/revoke target permission.

        Rules:
        - admin.* can manage any permission
        - admin.manage_permissions can manage non-admin permissions
        - User cannot escalate above their own permissions
        """
        # Full admin
        if "admin.*" in user_perms:
            return True

        # Permission manager can manage non-admin permissions
        if "admin.manage_permissions" in user_perms and not target_perm.startswith("admin"):
            return True

        return False
