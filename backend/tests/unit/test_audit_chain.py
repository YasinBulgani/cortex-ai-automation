"""Audit hash chain — pure fonksiyon testleri (DB gerekmez).

Canonical payload + compute_hash + verify_chain — bütün tamper edge case'leri
bu seviyede yakalanır. DB append + load integration testi ayrı koşum.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from app.domains.audit.chain import (
    ChainEvent,
    VerifyResult,
    canonical_payload,
    compute_hash,
    verify_chain,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _ev(seq: int = 1, action: str = "x.created", **kwargs) -> ChainEvent:
    return ChainEvent(
        ts=kwargs.get("ts", datetime(2026, 4, 19, 10, 0, seq, tzinfo=timezone.utc)),
        tenant_id=kwargs.get("tenant_id", "t1"),
        actor_user_id=kwargs.get("actor_user_id", "u1"),
        action=action,
        resource_type=kwargs.get("resource_type", "widget"),
        resource_id=kwargs.get("resource_id", f"wid-{seq}"),
        payload=kwargs.get("payload", {"field": "value"}),
        seq=seq,
    )


def _build_chain(n: int) -> List[ChainEvent]:
    prev_hash = ""
    out: List[ChainEvent] = []
    for i in range(1, n + 1):
        e = _ev(seq=i)
        e.prev_hash = prev_hash or None
        e.hash = compute_hash(prev_hash, e)
        out.append(e)
        prev_hash = e.hash
    return out


# ── Canonical payload ────────────────────────────────────────────────────


class TestCanonical:
    def test_deterministic_same_input(self) -> None:
        a = canonical_payload(_ev())
        b = canonical_payload(_ev())
        assert a == b

    def test_changes_with_ts(self) -> None:
        e1 = _ev(seq=1)
        e2 = _ev(seq=1)  # aynı seq ama farklı ts
        e2.ts = datetime(2026, 4, 19, 10, 5, 0, tzinfo=timezone.utc)
        assert canonical_payload(e1) != canonical_payload(e2)

    def test_payload_key_order_irrelevant(self) -> None:
        a = canonical_payload(_ev(payload={"a": 1, "b": 2}))
        b = canonical_payload(_ev(payload={"b": 2, "a": 1}))
        assert a == b

    def test_unicode_safe(self) -> None:
        e = _ev(payload={"ad": "Çağrı Özcan"})
        s = canonical_payload(e)
        assert "Çağrı" in s
        assert "Özcan" in s

    def test_naive_datetime_coerced_to_utc(self) -> None:
        e1 = _ev()
        e1.ts = datetime(2026, 4, 19, 10, 0, 1)  # naive
        e2 = _ev()
        e2.ts = datetime(2026, 4, 19, 10, 0, 1, tzinfo=timezone.utc)
        assert canonical_payload(e1) == canonical_payload(e2)


# ── compute_hash ─────────────────────────────────────────────────────────


class TestHash:
    def test_hash_is_sha256_hex(self) -> None:
        h = compute_hash("", _ev())
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_prev_hash_different_result(self) -> None:
        e = _ev()
        h1 = compute_hash("", e)
        h2 = compute_hash("aa" * 32, e)
        assert h1 != h2

    def test_tiny_payload_change_alters_hash(self) -> None:
        e1 = _ev(payload={"field": "value"})
        e2 = _ev(payload={"field": "value "})  # trailing space
        assert compute_hash("", e1) != compute_hash("", e2)


# ── verify_chain ─────────────────────────────────────────────────────────


class TestVerify:
    def test_empty_chain_ok(self) -> None:
        r = verify_chain([])
        assert r.ok is True
        assert r.total == 0
        assert r.verified == 0

    def test_valid_chain_verifies(self) -> None:
        chain = _build_chain(5)
        r = verify_chain(chain)
        assert r.ok is True
        assert r.total == 5
        assert r.verified == 5
        assert r.errors == []

    def test_detects_mid_tamper(self) -> None:
        chain = _build_chain(5)
        # Middle event payload'ını değiştir (hash'i güncellemeden)
        chain[2].payload = {"field": "TAMPERED"}
        r = verify_chain(chain)
        assert r.ok is False
        assert r.first_bad_seq == 3
        assert r.verified == 2  # ilk 2 geçerli
        assert r.errors
        assert "hash uyumsuz" in r.errors[0] or "prev_hash uyumsuz" in r.errors[0]

    def test_detects_first_event_tamper(self) -> None:
        chain = _build_chain(3)
        chain[0].payload = {"field": "BAD"}
        r = verify_chain(chain)
        assert r.ok is False
        assert r.first_bad_seq == 1
        assert r.verified == 0

    def test_detects_prev_hash_mismatch(self) -> None:
        chain = _build_chain(3)
        # Doğru payload ama prev_hash elle bozulmuş
        chain[1].prev_hash = "0" * 64
        r = verify_chain(chain)
        assert r.ok is False
        assert r.first_bad_seq == 2
        assert any("prev_hash uyumsuz" in e for e in r.errors)

    def test_detects_dropped_event(self) -> None:
        chain = _build_chain(5)
        # 3. olayı at — chain kopar
        truncated = [chain[0], chain[1], chain[3], chain[4]]
        r = verify_chain(truncated)
        assert r.ok is False

    def test_legacy_events_break_chain(self) -> None:
        # seq=None, hash=None olan eski kayıtlar zinciri kırar
        legacy = _ev(seq=1)
        legacy.seq = None
        legacy.hash = None
        r = verify_chain([legacy])
        assert r.ok is False
        assert "legacy" in r.errors[0]

    def test_out_of_order_events_sorted(self) -> None:
        chain = _build_chain(4)
        shuffled = [chain[2], chain[0], chain[3], chain[1]]
        r = verify_chain(shuffled)
        assert r.ok is True
        assert r.verified == 4

    def test_chain_grows_one_at_a_time(self) -> None:
        # N=1,2,...10 her adımda verify geçmeli
        prev_hash = ""
        chain: list = []
        for i in range(1, 11):
            e = _ev(seq=i)
            e.prev_hash = prev_hash or None
            e.hash = compute_hash(prev_hash, e)
            chain.append(e)
            prev_hash = e.hash

            r = verify_chain(chain)
            assert r.ok is True, f"n={i}: {r.errors}"
            assert r.verified == i
