"""Review workflow state machine for test case reviews.

State transitions:
    none → pending_review (reviewer requested)
    pending_review → approved/rejected (review completed)
    approved → none (reset approval)
    rejected → pending_review (re-review after fix)
"""

from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    """Review workflow states."""
    NONE = "none"  # No review needed
    PENDING = "pending_review"  # Awaiting reviewer
    APPROVED = "approved"  # Review passed
    REJECTED = "rejected"  # Review failed


class ReviewTransition:
    """Validates state machine transitions."""

    # Valid transitions: from_state -> [allowed_to_states]
    VALID_TRANSITIONS = {
        ReviewStatus.NONE: [ReviewStatus.PENDING],
        ReviewStatus.PENDING: [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.NONE],
        ReviewStatus.APPROVED: [ReviewStatus.NONE, ReviewStatus.PENDING],
        ReviewStatus.REJECTED: [ReviewStatus.PENDING, ReviewStatus.NONE],
    }

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        """Check if transition is allowed."""
        try:
            current_state = ReviewStatus(current)
            target_state = ReviewStatus(target)
            allowed = cls.VALID_TRANSITIONS.get(current_state, [])
            return target_state in allowed
        except ValueError:
            return False

    @classmethod
    def validate(cls, current: str, target: str) -> None:
        """Raise ValueError if transition invalid."""
        if not cls.can_transition(current, target):
            raise ValueError(
                f"Invalid review state transition: {current} → {target}. "
                f"Allowed: {cls.VALID_TRANSITIONS.get(current, [])}"
            )


def get_review_action(current: ReviewStatus, target: ReviewStatus) -> str:
    """Determine action label for state transition."""
    if target == ReviewStatus.PENDING:
        return "request_review" if current == ReviewStatus.NONE else "request_review_again"
    elif target == ReviewStatus.APPROVED:
        return "approve"
    elif target == ReviewStatus.REJECTED:
        return "reject"
    elif target == ReviewStatus.NONE:
        return "reset_review"
    return "unknown"
