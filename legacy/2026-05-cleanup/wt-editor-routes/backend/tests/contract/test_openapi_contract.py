"""
OpenAPI Contract Tests — Schemathesis ile property-based API test.

Backend'in urettigi OpenAPI spec'ine karsi otomatik test senaryolari
uretir ve calistirir. Spec'teki her endpoint icin gecerli ve gecersiz
payload'lar denenir; response schema uyumu dogrulanir.
"""
import os

import pytest

try:
    import schemathesis
except ImportError:
    pytest.skip("schemathesis not installed", allow_module_level=True)

from app.main import app


schema = schemathesis.from_asgi("/openapi.json", app=app)


@schema.parametrize()
@pytest.mark.contract
def test_openapi_spec_conformance(case):
    """Her endpoint icin OpenAPI spec'e uygunluk testi."""
    response = case.call_asgi()
    case.validate_response(response)
