# Risk Register

| ID | Risk | Olasılık | Etki | Mitigation | Owner | Last review |
|---|---|---|---|---|---|---|
| R-001 | Auth katmanında token leak | Düşük | S1 | Security review zorunlu, SEC-tag'li TC'ler smoke set'te | @yasin-bulgan | 2026-05-22 |
| R-002 | AI üretilen TC'ler kalitesiz | Orta | S3 | `_draft/` zorunlu human-review, `ai-quality.mjs` semantic lint | @yasin-bulgan | 2026-05-22 |
| R-003 | Engine features deprecation tamamlanmamış (65 dosya) | Yüksek | S2 | PR 4+'ta planlandı; şu an dokunulmuyor | @yasin-bulgan | 2026-05-22 |
| R-004 | Migration sırasında TC kaybı | Düşük | S1 | Concat-diff doğrulama (PR 3'te) | @yasin-bulgan | 2026-05-22 |
| R-005 | `docs/test-design/features/` ile `backend/tests/bdd/features/` TR/EN double-maintenance | Yüksek | S3 | PR 2'de 3 duplicate silinir, design-only 8'i `qa/`'ya taşınır | @yasin-bulgan | 2026-05-22 |
| R-006 | AI maliyet patlaması (ai-suggest) | Orta | S3 | Hard cap ($5/gün), max-cases=5, dry-run mode | @yasin-bulgan | 2026-05-22 |
| R-007 | Non-teknik QA git eşiği | Orta | S3 | `new-tc.mjs` interaktif, `run-record.mjs` (PR 4+) TUI | @yasin-bulgan | 2026-05-22 |
| R-008 | Dependency güncellemeleri Node tooling'i kırar | Düşük | S3 | `package.json` strict version, dependabot | @yasin-bulgan | 2026-05-22 |

## Severity tanımları

- **S1**: Critical — release stopper, data loss veya security breach
- **S2**: Major — feature broken, workaround zor
- **S3**: Moderate — feature partial, workaround var
- **S4**: Minor — kozmetik veya nadir edge case
