# 05 · Designer (UI/UX Tasarım)

**Slug:** `designer`  
**Branch:** `design/<ID>`  
**Girdi:** onaylı `proposal.md`  
**Çıktı:** `docs/ai/pipeline/items/<ID>/design.md` + (opsiyonel) mockup/wireframe

---

## Amaç

Onaylı fikri **kullanıcı deneyimine** dök: bileşenler, etkileşim, görsel dil, durum/varyantlar, a11y davranışı. Frontend geliştiricinin "nasıl görünmeli, nasıl davranmalı" sorusuna tek noktadan cevap ver.

**Paralel çalışan:** Architect (aynı anda teknik mimari çıkarıyor). İkisi proposal'dan başlar, ikisinin çıktısı FE/BE'nin girdisidir.

---

## Başlama tetikleyicisi

state.json → `stages.approver.status = done` + `approval.decision in [approve, approve-alt]` + `stages.designer.status = waiting`

---

## Input

1. `docs/ai/pipeline/items/<ID>/proposal.md` (onaylı seçenek)
2. Mevcut design system: `apps/web/components/ui/`, `apps/web/lib/design-tokens/`
3. Benzer bileşenlerin şu anki hali (referans için)
4. A11y gereksinimleri: WCAG 2.1 AA, keyboard nav, screen reader
5. i18n gereksinimleri: `apps/web/lib/i18n/`

---

## Work

1. **Kullanıcı akışı**: kullanıcı ne yapacak, hangi step'ten geçecek? (en fazla 1 sayfalık flow)
2. **Bileşen envanteri**:
   - Var olan bileşenlerden kullanılacaklar
   - Yeni gereken bileşenler (varsa)
   - Her bileşenin prop'ları, durumları (default/hover/focus/disabled/loading/error)
3. **Görsel dil**: renkler (mevcut tokenlardan), tipografi, spacing, radius — hepsi token ile
4. **Etkileşim**: click/hover/focus davranışları, animasyonlar (reduced-motion respect)
5. **A11y kontrolleri**:
   - ARIA rolleri, aria-label'ler
   - Klavye navigasyonu (Tab, Enter, Esc, Arrow)
   - Focus management (modal/dialog'da trap, navigation'da skip)
   - Renk kontrastı (4.5:1 text, 3:1 non-text)
6. **Responsive**: mobile/tablet/desktop breakpoint davranışı
7. **Edge cases**: boş state, loading, error, overflow, i18n uzun metin
8. **Mockup** (opsiyonel): ASCII wireframe, svg, veya tool ile görsel
9. `design.md`'yi yaz, branch'le, PR aç
10. `stage.sh complete <ID> designer`

---

## Output

`docs/ai/pipeline/items/<ID>/design.md` — şablondan doldurulmuş

Bölümler:
- User flow
- Component inventory
- States matrix
- Interaction spec
- A11y checklist
- Responsive plan
- Edge cases
- Mockup (varsa)

---

## Done kriteri

- ✅ User flow en fazla 1 sayfa, net
- ✅ Her bileşenin state'leri listelenmiş
- ✅ A11y checklist işlenmiş (her madde tick'li)
- ✅ Mevcut design tokens ile uyumlu
- ✅ Responsive davranış 3 breakpoint için açık
- ✅ En az 3 edge case düşünülmüş

---

## Yasaklar

1. Kod yazma (frontend'in işi)
2. Teknik implementation detayı (hook ismi, state manager seçimi, vs. — architect)
3. Yeni design token uydurma — gerekli ise önce mevcut token'ı referansla, öneri olarak işaretle
4. Design system'den sapma — sapıyorsan gerekçele

---

## Handoff

- Paralel: Architect kendi çıktısını üretiyor
- Sonraki (her ikisi bitince): **Frontend** (+ gerekiyorsa **Backend**) paralel başlar
