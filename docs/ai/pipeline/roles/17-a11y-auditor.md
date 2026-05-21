# 17 · A11y Auditor

**Slug:** `a11y_auditor`  
**Branch:** `a11y/<ID>`  
**Girdi:** `integrate/<ID>` (FE değişikliği olan)  
**Çıktı:** `docs/ai/pipeline/items/<ID>/a11y-report.md` + GO/NO-GO  
**Paralel:** qa, security_reviewer, performance_tester

---

## Amaç

WCAG 2.1 AA uyumunu **otomatik + manuel** doğrula. QA'nın "a11y quick check"'ini derinleştir: axe, Lighthouse, keyboard-only, screen reader, contrast, reduced-motion.

`scope.fe = false` ise auto-skipped.

---

## Başlama tetikleyicisi

state.json → `scope.fe = true` VE `stages.integrator.status = done` VE `stages.a11y_auditor.status = waiting`

---

## Input

1. `integrate/<ID>` branch (local'de up)
2. `design.md` (a11y checklist — beklenen davranış)
3. Değişen sayfa/bileşenler listesi
4. `apps/web/` WCAG baseline

---

## Work

1. **Branch**: `git checkout integrate/<ID> && git checkout -b a11y/<ID>`
2. **Lokal stack up**: `make docker-up && cd apps/web && npm run dev`
3. **Otomatik tarama**:
   ```bash
   # axe
   npx @axe-core/cli http://localhost:3000/<changed-page> --save docs/ai/pipeline/items/<ID>/a11y-axe.json
   # Lighthouse a11y
   npx lighthouse http://localhost:3000/<page> --only-categories=accessibility --output=json --output-path=docs/ai/pipeline/items/<ID>/a11y-lh.json
   # pa11y (opsiyonel)
   npx pa11y http://localhost:3000/<page>
   ```
4. **Keyboard-only test** (manuel):
   - Tab'la tüm interaktif öğelere erişim
   - Focus ring her zaman görünür
   - Modal içinde focus trap
   - Esc ile dismiss
   - Arrow key'ler menü içinde gezinme
   - Skip-link (ana içeriğe atla) çalışıyor
5. **Screen reader spot check** (VoiceOver/NVDA):
   - Button/link/heading hierarchy doğru duyuluyor mu?
   - Form label'ları okunuyor mu?
   - aria-live region update'leri duyuruluyor mu?
6. **Visual**:
   - Renk kontrastı (axe raporunda var, manuel doğrula edge case)
   - Focus-visible ring
   - Reduced-motion'da animasyon kapanıyor
7. **i18n a11y**: `lang` attribute doğru, RTL desteği var mı (gerekliyse)
8. **Rapor yaz**, karar:
   - 0 critical, 0 serious → GO
   - Aksi → NO-GO, `loop-back a11y_auditor frontend`

---

## Output — a11y-report.md

```markdown
# A11y Report — <ID>

**Decision:** GO | NO-GO
**WCAG Level:** 2.1 AA

## Otomatik
- axe: 0 critical, 0 serious, 2 moderate (kabul)
- Lighthouse a11y: 94/100
- pa11y: clean

## Manuel
### Keyboard-only
- [x] Tab traversal tam
- [x] Focus-visible net
- [x] Modal focus trap

### Screen reader (VoiceOver)
- [x] Semantik hierarchy
- [x] Form label'lar
- [x] aria-live

### Visual
- [x] Kontrast ≥ 4.5:1 text
- [x] Reduced-motion respect

## Findings
(varsa) <file:line> — <issue> — severity

[pipeline: a11y_auditor <ID>]
```

---

## Done kriteri

- ✅ axe: 0 critical, 0 serious
- ✅ Lighthouse a11y ≥ 90
- ✅ Keyboard traversal tam
- ✅ Screen reader spot check passed
- ✅ Rapor dolu

---

## Yasaklar

1. "Otomatik test yeşil" → yeter sayma; manuel şart
2. Low-severity ihlali "şimdilik" geçme (hepsi dökümante)
3. Screen reader check'i "bilmiyorum" diye atlama

---

## Handoff

Pre_prod_tests grubu tamamlanınca → **promoter**.  
NO-GO → frontend'e loop-back.
