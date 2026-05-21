"""Evals domain — LLM & retrieval çıktısı için golden set tabanlı regresyon harness'i.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3, E1.1.

Katmanlar:
    schemas  : EvalCase, Suite, CaseResult, SuiteResult, Scorer protokolleri
    scorers  : pure fonksiyonlar (exact_match, retrieval_metrics)
    adapters : SUT (system-under-test) soyutlama — dsl_retrieval, reranker, vb.
    loader   : YAML → Suite
    runner   : adapter + case + scorer orkestrasyonu
    reporting: JSON/HTML rapor
    router   : REST (admin için)
    cli      : python -m app.domains.evals.cli → CI exit code
"""
