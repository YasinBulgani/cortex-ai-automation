"""DSL cross-encoder reranker için unit testleri.

Gerçek sentence-transformers / torch modeli İNDİRİLMEZ — tüm CrossEncoder
çağrıları monkeypatch ile mock'lanır. Bu sayede testler CI'da sentence-
transformers kurulu olmasa bile çalışır.
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import List

import pytest

from app.domains.dsl.reranker import DslReranker


@dataclass
class _FakeCandidate:
    """Test için SemanticHit benzeri minimal aday nesne."""

    id: str
    text: str


def _text_of(c: _FakeCandidate) -> str:
    return c.text


@pytest.fixture
def reranker(monkeypatch: pytest.MonkeyPatch) -> DslReranker:
    """Her test için temiz bir DslReranker örneği."""
    # Singleton'daki önceki state'i kirletmemek için yeni instance
    r = DslReranker()
    # Env temizle — her test kendi flag'ini set edecek
    for key in (
        "AI_MODEL_RERANKER_ENABLED",
        "AI_MODEL_RERANKER",
        "AI_MODEL_RERANKER_TOP_K_IN",
        "AI_MODEL_RERANKER_TOP_K_OUT",
        "AI_MODEL_RERANKER_DEVICE",
    ):
        monkeypatch.delenv(key, raising=False)
    return r


def _install_fake_sentence_transformers(
    monkeypatch: pytest.MonkeyPatch,
    predictions_by_pair: dict,
    *,
    raise_on_init: bool = False,
    raise_on_predict: bool = False,
) -> list[tuple]:
    """Sahte ``sentence_transformers.CrossEncoder`` modülü yerleştir.

    Args:
        predictions_by_pair: {(query, candidate_text): score} map — predict
            çağrısında bu dict'ten skor okunur, yoksa 0 döner.
        raise_on_init: CrossEncoder() init'inde hata fırlat (disk/network fail)
        raise_on_predict: predict() çağrısında hata fırlat

    Returns:
        predict() çağrılarının logu: her çağrıda verilen (pairs) tuple listesi.
    """
    calls: list[tuple] = []

    class _FakeCrossEncoder:
        def __init__(self, model_name: str, *, device: str = "cpu") -> None:
            if raise_on_init:
                raise RuntimeError("disk-not-found")
            self.model_name = model_name
            self.device = device

        def predict(self, pairs):
            calls.append(tuple(pairs))
            if raise_on_predict:
                raise RuntimeError("predict-boom")
            return [
                float(predictions_by_pair.get(tuple(p), 0.0)) for p in pairs
            ]

    fake_mod = types.ModuleType("sentence_transformers")
    fake_mod.CrossEncoder = _FakeCrossEncoder  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_mod)
    return calls


# ── is_enabled() env davranışı ──────────────────────────────────────────────


def test_is_enabled_default_false(reranker: DslReranker) -> None:
    assert reranker.is_enabled() is False


@pytest.mark.parametrize("value", ["true", "True", "1", "yes", "on"])
def test_is_enabled_truthy_values(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", value)
    assert reranker.is_enabled() is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
def test_is_enabled_falsy_values(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", value)
    assert reranker.is_enabled() is False


# ── rerank() pass-through davranışları ──────────────────────────────────────


def test_rerank_disabled_returns_passthrough_top_k(
    reranker: DslReranker,
) -> None:
    cands = [_FakeCandidate(id=str(i), text=f"c{i}") for i in range(10)]
    result = reranker.rerank("q", cands, text_of=_text_of, top_k=3)
    # Flag kapalı — retrieval sırası korunmalı, sadece k ile kırpılmalı
    assert [c.id for c in result] == ["0", "1", "2"]


def test_rerank_empty_returns_empty(reranker: DslReranker) -> None:
    result = reranker.rerank("q", [], text_of=_text_of, top_k=5)
    assert result == []


def test_rerank_single_candidate_returns_as_is(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Flag açık olsa bile tek aday için model yüklenmemeli
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    cands = [_FakeCandidate(id="only", text="solo")]
    result = reranker.rerank("q", cands, text_of=_text_of)
    assert len(result) == 1
    assert result[0].id == "only"
    # Lazy loader'ın tetiklenmediğini doğrula
    assert reranker._load_attempted is False  # type: ignore[attr-defined]


# ── rerank() mock modelle sıralama ──────────────────────────────────────────


def test_rerank_reorders_by_model_score(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    cands = [
        _FakeCandidate(id="a", text="open_url"),
        _FakeCandidate(id="b", text="i_press"),
        _FakeCandidate(id="c", text="fill_search"),
    ]
    # Retrieval'da "i_press" yanlışlıkla yukarıda ama cross-encoder:
    #   open_url    → yüksek (gerçek parafraz eşleşmesi)
    #   fill_search → orta (ikinci en iyi)
    #   i_press     → düşük (yanlış eşleşme, demote edilmeli)
    predictions = {
        ("İletişim formunu aç", "open_url"): 0.95,
        ("İletişim formunu aç", "i_press"): 0.05,
        ("İletişim formunu aç", "fill_search"): 0.40,
    }
    calls = _install_fake_sentence_transformers(monkeypatch, predictions)

    result = reranker.rerank(
        "İletişim formunu aç", cands, text_of=_text_of, top_k=2
    )
    assert [c.id for c in result] == ["a", "c"]
    # Model tek bir predict() çağrısıyla tüm çiftleri aldı
    assert len(calls) == 1
    assert len(calls[0]) == 3


def test_rerank_tie_preserves_retrieval_order(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    cands = [
        _FakeCandidate(id="first", text="t1"),
        _FakeCandidate(id="second", text="t2"),
        _FakeCandidate(id="third", text="t3"),
    ]
    # Hepsi aynı skor — retrieval sırası korunmalı
    predictions = {
        ("q", "t1"): 0.5,
        ("q", "t2"): 0.5,
        ("q", "t3"): 0.5,
    }
    _install_fake_sentence_transformers(monkeypatch, predictions)

    result = reranker.rerank("q", cands, text_of=_text_of, top_k=3)
    assert [c.id for c in result] == ["first", "second", "third"]


def test_rerank_respects_top_k_env(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    monkeypatch.setenv("AI_MODEL_RERANKER_TOP_K_OUT", "2")
    cands = [_FakeCandidate(id=str(i), text=f"c{i}") for i in range(5)]
    predictions = {("q", f"c{i}"): 1.0 / (i + 1) for i in range(5)}
    _install_fake_sentence_transformers(monkeypatch, predictions)

    # top_k belirtilmedi → env'den AI_MODEL_RERANKER_TOP_K_OUT=2
    result = reranker.rerank("q", cands, text_of=_text_of)
    assert len(result) == 2
    # En yüksek skorlular sırayla gelir: 1/(1), 1/(2) → idx 0, 1
    assert [c.id for c in result] == ["0", "1"]


# ── Hata kurtarma ──────────────────────────────────────────────────────────


def test_rerank_fallback_when_sentence_transformers_missing(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    # Modülü sil (ImportError zorla)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    cands = [_FakeCandidate(id=str(i), text=f"c{i}") for i in range(4)]
    result = reranker.rerank("q", cands, text_of=_text_of, top_k=2)
    # ImportError → sessiz pass-through, retrieval sırası + kırpma
    assert [c.id for c in result] == ["0", "1"]
    assert reranker._load_failed_reason is not None  # type: ignore[attr-defined]
    assert "sentence-transformers" in reranker._load_failed_reason  # type: ignore[attr-defined]


def test_rerank_fallback_when_model_init_fails(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    _install_fake_sentence_transformers(
        monkeypatch, {}, raise_on_init=True
    )

    cands = [_FakeCandidate(id=str(i), text=f"c{i}") for i in range(3)]
    result = reranker.rerank("q", cands, text_of=_text_of, top_k=2)
    assert [c.id for c in result] == ["0", "1"]
    assert "Model yüklenemedi" in (reranker._load_failed_reason or "")  # type: ignore[attr-defined]


def test_rerank_fallback_when_predict_fails(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    _install_fake_sentence_transformers(
        monkeypatch, {}, raise_on_predict=True
    )

    cands = [_FakeCandidate(id=str(i), text=f"c{i}") for i in range(3)]
    result = reranker.rerank("q", cands, text_of=_text_of, top_k=2)
    # predict() patladı → retrieval sırası + kırpma
    assert [c.id for c in result] == ["0", "1"]


def test_load_attempted_only_once(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yükleme başarısız olursa sonraki çağrılarda tekrar denenmemeli."""
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    _install_fake_sentence_transformers(
        monkeypatch, {}, raise_on_init=True
    )

    cands = [_FakeCandidate(id="a", text="t"), _FakeCandidate(id="b", text="u")]
    reranker.rerank("q", cands, text_of=_text_of, top_k=1)
    reason_before = reranker._load_failed_reason  # type: ignore[attr-defined]
    reranker.rerank("q", cands, text_of=_text_of, top_k=1)
    reason_after = reranker._load_failed_reason  # type: ignore[attr-defined]
    # Tek bir başarısızlık log'u, sonraki çağrıda tekrar yüklemeye girmedi
    assert reason_before == reason_after
    assert reranker._load_attempted is True  # type: ignore[attr-defined]


# ── info() telemetri ────────────────────────────────────────────────────────


def test_info_reflects_state(
    reranker: DslReranker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_MODEL_RERANKER_ENABLED", "true")
    monkeypatch.setenv("AI_MODEL_RERANKER", "custom/model-v2")
    monkeypatch.setenv("AI_MODEL_RERANKER_TOP_K_IN", "30")
    monkeypatch.setenv("AI_MODEL_RERANKER_TOP_K_OUT", "7")
    monkeypatch.setenv("AI_MODEL_RERANKER_DEVICE", "mps")

    info = reranker.info()
    assert info["enabled"] is True
    assert info["model"] == "custom/model-v2"
    assert info["top_k_in"] == 30
    assert info["top_k_out"] == 7
    assert info["device"] == "mps"
    # Henüz rerank çağrılmadı → loaded False
    assert info["loaded"] is False
    assert info["load_attempted"] is False
