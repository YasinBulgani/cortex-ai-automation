"""Custom assertion helpers for API response validation."""

import httpx


def assert_status(response: httpx.Response, expected: int, msg: str = "") -> None:
    assert response.status_code == expected, (
        f"Expected {expected}, got {response.status_code}. "
        f"{msg} Body: {response.text[:500]}"
    )


def assert_json_has_keys(data: dict, keys: list[str]) -> None:
    missing = [k for k in keys if k not in data]
    assert not missing, f"Missing keys: {missing}. Got: {list(data.keys())}"


def assert_list_not_empty(data: list) -> None:
    assert isinstance(data, list) and len(data) > 0, f"Expected non-empty list, got: {data}"


def assert_validation_error(response: httpx.Response) -> None:
    assert response.status_code == 422, (
        f"Expected 422 Validation Error, got {response.status_code}. Body: {response.text[:500]}"
    )


def assert_not_found(response: httpx.Response) -> None:
    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}. Body: {response.text[:500]}"
    )


def assert_unauthorized(response: httpx.Response) -> None:
    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}. Body: {response.text[:500]}"
    )


def assert_created(response: httpx.Response) -> None:
    assert response.status_code == 201, (
        f"Expected 201 Created, got {response.status_code}. Body: {response.text[:500]}"
    )
