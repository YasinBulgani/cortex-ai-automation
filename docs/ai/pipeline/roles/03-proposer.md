# 03 · Proposer (Çözüm Öneren)

**Slug:** `proposer`  
**Branch:** `propose/<ID>`  
**Girdi:** onaylı `gap-analysis.md`  
**Çıktı:** `docs/ai/pipeline/items/<ID>/proposal.md`

---

## Amaç

Doğrulanmış gap'e **çözüm seçenekleri** üret. En az 2, tercihen 3 seçenek. Her seçeneğin pro/con'larını yaz. Önerilen seçeneği belirt ve gerekçelendir.

Bu rol **fikir üretir** — kod yazmaz, tasarım yapmaz.

---

## Başlama tetikleyicisi

state.json → `stages.validator.status = done` + `approval.decision = approve` + `stages.proposer.status = waiting`

**Loop-back tetikleyicisi:** Approver `revise` dediyse, `feedback_loops[last].reason`'ı oku, proposal'ı revize et.

---

## Input

1. `docs/ai/pipeline/items/<ID>/gap-analysis.md` (doğrulanmış bulgu)
2. Gap'in dokundugu kod bölgesi (anlamak için oku, değiştirme)
3. `docs/ai/GROUNDING.md` — proje context, tercihler, stack
4. Varsa `feedback_loops[last]` — approver ne sebeple revize istedi

---

## Work

1. **Problem alanını anla**: gap'in kökü nedir? Sadece belirtiyi değil sebebi hedefle.
2. **3 seçenek üret**:
   - **Seçenek A** — minimum viable (en hızlı)
   - **Seçenek B** — önerilen (best tradeoff)
   - **Seçenek C** — ideal (en yüksek kalite, muhtemelen overkill)
3. Her seçenek için:
   - Teknik özet (1 paragraf)
   - Kapsam (FE / BE / ikisi de)
   - Tahmini efor (S/M/L/XL)
   - Risk/yan etki
   - Breaking change var mı?
4. **Öneriyi işaretle** (genelde B) ve gerekçelendir
5. `proposal.md`'yi yaz (şablondan)
6. Branch aç, commit at:
   ```bash
   git checkout test && git pull && git checkout -b propose/<ID>
   git add docs/ai/pipeline/items/<ID>/proposal.md docs/ai/pipeline/state.json
   git commit -m "propose: <ID> — <kısa başlık> [pipeline: proposer <ID>]" --no-verify
   git push -u origin propose/<ID>
   gh pr create --base test --title "..." --body "..."
   ```
7. `stage.sh complete <ID> proposer`

---

## Output

`docs/ai/pipeline/items/<ID>/proposal.md` — şablondan doldurulmuş, 3 seçenekli

---

## Done kriteri

- ✅ En az 2 seçenek var
- ✅ Önerilen seçenek işaretli ve gerekçeli
- ✅ Her seçeneğin tahmini eforu ve risk'i yazılı
- ✅ Breaking change'ler açık
- ✅ PR `test`'e açık

---

## Yasaklar

1. Kod yazma (designer/architect'e bırak)
2. Tek seçenek sunma (≥2 zorunlu)
3. "Daha sonra düşünürüz" tarzı muğlaklık — her seçenek somut olmalı
4. Gap'i değiştirme — sen çözümü öneriyorsun, bulguyu değil

---

## Loop-back modu (approver "revise" dediyse)

1. `feedback_loops[last].reason`'ı oku
2. Hangi seçenek revize edilecek? Yeni seçenek mi ekle, mevcut'u değiştir mi?
3. Değişiklikleri **mevcut proposal.md**'ye işle, revision bölümüne eklemek yerine üstüne yaz
4. Revision history'yi dosyanın sonuna ekle:
   ```
   ## Revision History
   - v1: 2026-04-17 — ilk teklif
   - v2: 2026-04-17 — approver feedback: persist stratejisi eklendi
   ```

---

## Handoff

Sonraki rol: **Approver**. state.json → `approver.status = waiting`.
