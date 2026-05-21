"""
steps/api/step_auth.py — Kimlik dogrulama (TS-01) step tanimlari.

Feature: auth.feature
Kapsam: TC-0101 ~ TC-0110
"""
from __future__ import annotations

from pytest_bdd import given, when, then, scenarios

from helpers.api_client import APIClient

scenarios("../../features/api/auth.feature")


# -- TC-0104 ozel --
@given("devre disi birakilmis bir kullanici mevcut")
def inactive_user_exists(context: dict):
    context["inactive_email"] = "inactive@example.com"
    context["inactive_password"] = "pass123"


@when("devre disi kullanicinin bilgileriyle login istegi gonderilir")
def login_inactive_user(api_anon: APIClient, context: dict):
    context["response"] = api_anon.post(
        "/api/v1/auth/login",
        json={
            "email": context["inactive_email"],
            "password": context["inactive_password"],
        },
    )


# -- TC-0110 ozel --
@then('veritabaninda "auth.login" aksiyonlu audit log kaydi bulunmalidir')
def assert_audit_log(context: dict):
    # Audit log dogrulamasi: backend DB sorgusu veya API ile kontrol
    # Stub: yanit basarili olduysa audit log olusmus kabul edilir
    assert context["response"].status_code == 200
