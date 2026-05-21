"""CoverUp Self-Healing — Faz A (library + orchestrator).

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.1.

Alt modüller:
    schemas          — FailureEvent, HealingProposal, HealingRun
    locator_healer   — LLM ile alternatif selector önerileri + confidence
    patch_applier    — kırık selector'ı dosyada güvenli replace
    github_client    — PAT tabanlı minimal GitHub API istemcisi
                       (App interface'e geçişte değişmeyecek)
    orchestrator     — failure → heal → patch → PR zinciri (feature-flag'li)

Faz B (bu sprint dışı):
    * Engine webhook endpoint (/coverup/heal/events) + router
    * Dashboard UI (heal edilen PR'ların listesi)
    * CI annotation → webhook integration örneği
"""
