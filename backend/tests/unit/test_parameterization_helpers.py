"""Pytest parameterization helpers for common test patterns.

Provides utilities to reduce boilerplate when writing parameterized tests:
  - cartesian_product(): generates n-dimensional test matrices
  - boundary_values(): generates typical boundary value inputs
  - role_matrix(): generates RBAC test matrices
  - http_status_matrix(): generates HTTP method + status combos
"""

from __future__ import annotations

import itertools
from typing import Any, Callable


def cartesian_product(
    *iterables: list[Any] | tuple[Any, ...],
    exclude: set[tuple[Any, ...]] | None = None,
) -> list[tuple[Any, ...]]:
    """Generate n-dimensional Cartesian product of input iterables.

    Excludes specific combinations via `exclude` set.

    Example:
        test_inputs = cartesian_product([1, 2], ["a", "b"], exclude={(1, "b")})
        # Returns: [(1, "a"), (2, "a"), (2, "b")]
    """
    result = list(itertools.product(*iterables))
    if exclude:
        result = [combo for combo in result if combo not in exclude]
    return result


def boundary_values(
    *,
    int_min: int = 0,
    int_max: int = 2**31 - 1,
    str_min: int = 0,
    str_max: int = 1000,
) -> dict[str, list[Any]]:
    """Generate typical boundary value test inputs.

    Returns dict with categories:
      - 'integers': [min, min+1, 0, max-1, max, negative, overflow]
      - 'strings': [empty, single-char, normal, max-length, overflow-length]
      - 'nulls': [None, empty containers]
      - 'special': [unicode, whitespace-only]
    """
    return {
        "integers": [
            int_min,
            int_min + 1,
            0,
            -1,
            int_max - 1,
            int_max,
        ],
        "strings": [
            "",
            "a",
            "normal string",
            "x" * str_max,
            "x" * (str_max + 1),
        ],
        "nulls": [
            None,
            [],
            {},
            set(),
        ],
        "special": [
            "   ",  # whitespace-only
            "\n\t\r",  # control characters
            "日本語",  # unicode
            "emoji 🚀",
        ],
    }


def role_matrix(
    *,
    roles: list[str] | None = None,
    endpoints: list[str] | None = None,
    default_allowed: bool = False,
) -> list[tuple[str, str, bool]]:
    """Generate (role, endpoint, expected_allowed) tuples for RBAC testing.

    Example:
        matrix = role_matrix(
            roles=["admin", "tester", "viewer"],
            endpoints=["/projects", "/settings"],
            default_allowed=False,
        )
        # For each (role, endpoint) pair, returns expected_allowed=False
    """
    if roles is None:
        roles = ["admin", "operator", "tester", "viewer"]
    if endpoints is None:
        endpoints = ["/api/v1/projects", "/api/v1/settings"]

    return [
        (role, endpoint, default_allowed)
        for role in roles
        for endpoint in endpoints
    ]


def http_status_matrix(
    *,
    methods: list[str] | None = None,
    success_status: int = 200,
    error_statuses: list[int] | None = None,
) -> list[tuple[str, int]]:
    """Generate (method, expected_status) tuples for HTTP endpoint testing.

    Example:
        matrix = http_status_matrix(
            methods=["GET", "POST"],
            success_status=200,
            error_statuses=[400, 401, 403, 500],
        )
        # Returns: [("GET", 200), ("POST", 200), ("GET", 400), ...]
    """
    if methods is None:
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if error_statuses is None:
        error_statuses = [400, 401, 403, 404, 409, 500, 503]

    # All success cases first, then error cases
    result = [(method, success_status) for method in methods]
    result.extend([(methods[0], status) for status in error_statuses])  # Just first method for brevity
    return result


def paginated_inputs(
    total_items: int = 1000,
    page_size: int = 10,
) -> list[tuple[int, int, int]]:
    """Generate (page, page_size, expected_count) tuples for pagination testing.

    Example:
        inputs = paginated_inputs(total_items=100, page_size=10)
        # Returns: [(1, 10, 10), (2, 10, 10), ..., (10, 10, 10), (11, 10, 0)]
    """
    result = []
    last_page_items = total_items % page_size or page_size
    num_full_pages = (total_items + page_size - 1) // page_size

    for page in range(1, num_full_pages + 1):
        result.append((page, page_size, last_page_items if page == num_full_pages else page_size))

    # Out-of-bounds page
    result.append((num_full_pages + 1, page_size, 0))
    return result


def decorator_parameterize_with_ids(
    arg_names: str,
    arg_values: list[tuple[Any, ...] | Any],
    ids: list[str] | Callable[[Any], str] | None = None,
) -> Callable:
    """Convenience decorator that applies @pytest.mark.parametrize with smart IDs.

    If ids is None, auto-generates from arg_values (useful for tuples).
    If ids is a callable, applies it to each value for the ID.

    Example:
        @decorator_parameterize_with_ids(
            "role,allowed",
            [("admin", True), ("viewer", False)],
        )
        def test_permission(role, allowed):
            ...
    """
    import pytest

    def decorator(func: Callable) -> Callable:
        # Auto-generate IDs if not provided
        computed_ids = None
        if ids is None and isinstance(arg_values, list) and arg_values:
            # Try to auto-generate from first element
            first = arg_values[0]
            if isinstance(first, (tuple, list)):
                computed_ids = [f"{'-'.join(str(x) for x in row)}" for row in arg_values]
        elif callable(ids):
            computed_ids = [ids(val) for val in arg_values]
        else:
            computed_ids = ids

        return pytest.mark.parametrize(arg_names, arg_values, ids=computed_ids)(func)

    return decorator


# ───────────────────────────────────────────────────────────────────────────
# Integration test: verify helpers work as expected
# ───────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example: cartesian product for 3-way combo
    print("Cartesian product (2x3x2):")
    product = cartesian_product([1, 2], ["a", "b", "c"], [True, False])
    print(f"  Count: {len(product)}")
    print(f"  First 3: {product[:3]}")

    # Example: boundary values
    print("\nBoundary values:")
    boundaries = boundary_values(int_max=100, str_max=50)
    print(f"  Integer boundaries: {boundaries['integers']}")
    print(f"  String boundaries count: {len(boundaries['strings'])}")

    # Example: role matrix
    print("\nRole matrix (3 roles x 2 endpoints):")
    matrix = role_matrix(roles=["admin", "tester", "viewer"], endpoints=["/projects", "/settings"])
    print(f"  Count: {len(matrix)}")
    print(f"  Sample: {matrix[0]}")

    # Example: pagination inputs
    print("\nPagination (100 items, 10/page):")
    pages = paginated_inputs(total_items=100, page_size=10)
    print(f"  Page count: {len(pages)}")
    print(f"  Sample (page 5): {pages[4]}")
    print(f"  Out-of-bounds: {pages[-1]}")
