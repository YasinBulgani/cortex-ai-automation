# Agent Active Work Tracker

Bu dosya, aynı repo'da paralel çalışan Cursor agent'ların **kim ne üzerinde çalışıyor** bilgisini paylaşmasını sağlar. Amaç: branch çakışması, stash karışıklığı ve commit yanlış-yerine-düşmesini önlemek.

Bu dosya mutlak kaynak **değildir** — git state asıl kaynaktır. Bu dosya sadece koordinasyon ipucudur.

İlgili kural: [`.cursor/rules/concurrent-git-hygiene.mdc`](../.cursor/rules/concurrent-git-hygiene.mdc)

---

## Nasıl kullanılır

### Agent olarak sen

1. **Yeni iş başlarken** — Aşağıdaki tabloya kendi satırını ekle:
   ```
   | <agent-id> | <branch-name> | <YYYY-MM-DD> | <kısa kapsam> | <YYYY-MM-DD HH:MM> |
   ```
2. **PR açınca** — "Son güncelleme" ve "Durum" kolonlarını güncelle (`PR #<no>` ekle)
3. **PR merge olunca** — Satırını kaldır VEYA **Arşiv** bölümüne taşı
4. **Başka agent'ın satırına ASLA dokunma** — yalnız kendi satırını yönet

### Özel durumlar

- **Başka agent'ın WIP'ini working tree'de görürsen** → stash'la, ismini `NOT-MINE-*` ile etiketle, pop etme. Ondan sonra tabloya bu gözlemi not olarak ekleyebilirsin (opsiyonel).
- **Branch kaybolursa** → bu tablodan son kullanan agent'a bakılabilir.

---

## Aktif Çalışmalar

> Güncel tarih: 2026-04-19 (bu dosyanın eklendiği sprint)

| Agent ID | Branch | Başladı | Kapsam | Durum | Son güncelleme |
|---|---|---|---|---|---|
| _(agent'lar kendi satırlarını buraya ekler)_ | | | | | |

### Bilinen paralel iş alanları (tarihsel, 2026-04-19 itibarıyla)

Aşağıdakiler oturum sırasında gözlemlenmiş paralel aktivitelerdir. Orijinal sahipleri kendi satırlarını güncellemelidir:

| Branch gözlemlendi | Muhtemel kapsam | Observer notu |
|---|---|---|
| `fix/p0-blockers` | router_registry, main.py temizlik, feature_flags | Yoğun modification; P0-001 ile paralel |
| `fix/p2-ui-turkish-normalization` | UI Turkish text normalization | P2 UX düzeltmesi |
| `feat/fe-a11y-GAP-001` | Frontend a11y GAP-001 (merge oldu → #49) | Tamamlandı |
| `feat/pipeline-conductor-full` | 25-rollü pipeline conductor (merge oldu → #47) | Tamamlandı |

---

## Arşiv — Kapanmış PR'lar (son 30 gün)

Referans için. Merge'den sonra agent satırı buraya taşınır.

| Agent ID | Branch | PR | Merge tarihi | Kısa özet |
|---|---|---|---|---|
| pipeline-conductor-agent | `feat/pipeline-conductor-full` | #47 | 2026-04-19 | 25-rollü agent orkestrasyon + Ollama + Makefile.pipeline |
| fe-a11y-agent | `feat/fe-a11y-GAP-001` | #49 | 2026-04-19 | Accessibility GAP-001 — sidebar keyboard nav + planlama dokümanları |
| engine-eval | `feat/engine-eval-ci-gate` | #48 | _(OPEN)_ | Engine eval gate workflow — grounding-only PR check |
| engine-eval | `feat/backend-dsl-reranker` | #50 | _(OPEN)_ | Turkish cross-encoder reranker — opt-in, graceful fallback |
| engine-eval | `feat/backend-a11y-ai-analyzer` | #52 | _(OPEN)_ | AI destekli accessibility violation analyzer — opt-in |
| engine-eval | `fix/p0-main-imports` | #53 | _(OPEN)_ | main.py import restore + create_app wiring |

---

## Rozet referansı (commit mesajlarındaki etiketler)

Commit'lerinin sonuna standart formatta rozetleri koy:

```
<commit mesajı>

[agent: <agent-id>]
[plan: <plan-id, varsa>]
[phase: <faz-numarası, varsa>]
```

Örnek:
```
feat(dsl): Turkish cross-encoder reranker — opt-in, graceful fallback

...

[agent: engine-eval]
[plan: UX-F2-202]
[phase: 2]
```

Böylece:
- `git log --grep="[agent: engine-eval]"` → kendi işini izlersin
- `git log --grep="[plan: UX-"` → UX planı uygulamasının ilerlemesini görürsün
- `git log --grep="[phase: 1]"` → Faz 1 commit'lerinin listesi

---

## Konvansiyon: Agent ID'ler

Tekrar kullanılan agent kimlikleri. Yenisini eklerken burada rezerve et:

| Agent ID | Açıklama | Tipik branch prefix |
|---|---|---|
| `engine-eval` | Engine & eval harness, DSL, reranker | `feat/backend-*`, `feat/engine-*`, `fix/p0-*` |
| `design-pass` | UI tasarım cilası | `feat/design-*` |
| `fe-a11y-agent` | Frontend accessibility | `feat/fe-a11y-*`, `fix/p2-ui-*` |
| `pipeline-conductor-agent` | 25-rollü orchestration | `feat/pipeline-*` |
| `mobile-agent` | Mobile automation | `feat/mobile-*` |
| `yb-qa-agent` | QA otomasyon | `test/*` |
| `docs-agent` | Dokümantasyon | `docs/*`, `chore/docs-*` |

---

## Notlar

- Bu dosya okunabilir mi diye haftada bir kontrol et — çöp birikmesin
- Agent tarafından otomatik güncelleme zorunlu değil (opsiyonel — agent istemediği sürece)
- Son çare: `git log --grep="[agent: X]" --since="1 week ago"` → tablodan kaybolan agent'ın son aktivitesi
