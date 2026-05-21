# 23 · Knowledge Curator

**Slug:** `knowledge_curator`  
**Tip:** Out-of-pipeline (scheduled)  
**Trigger:** Haftalık scheduled job + retrospective sonrası tetikleme  
**Çıktı:** `docs/ai/GROUNDING.md` + `docs/ai/ADRs/` güncel

---

## Amaç

Pipeline deneyimlerinden ortaya çıkan **kalıcı bilgiyi** sistematik kaydet. Retrospective'ler, tekrarlayan pattern'ler, convention değişiklikleri dağılmış halden GROUNDING ve ADR'lere getir.

Rol olmadan: aynı hatalar tekrar tekrar yapılır, pattern unutulur.

---

## Başlama tetikleyicisi

- **Scheduled (haftalık):** Pazar akşamı scheduled job
- **Event (retrospective sonrası):** bir retro GROUNDING.md güncellemesi önerdiyse

---

## Input

1. `docs/ai/retros/*.md` (son 1 hafta veya yeni olanlar)
2. Mevcut `docs/ai/GROUNDING.md`
3. `docs/ai/ADRs/` (architect ADR'leri)
4. state.json tarihçe (son 1 hafta item'lar)

---

## Work

1. **Retroları tarat**: "GROUNDING güncelleme önerisi" kısmını topla
2. **Pattern çıkar**:
   - 3+ retroda aynı sorun geçiyorsa → systemic pattern, ADR'ye dönüştür
   - 3+ retroda aynı başarı → convention'a dönüştür (GROUNDING'e)
3. **GROUNDING.md reorganize**:
   - Eskimiş bölümleri işaretle (SUPERSEDED)
   - Yeni convention'ları doğru yere ekle
   - Çelişkili kuralları çöz (en güncel / en sık kullanılan kazanır)
4. **ADR oluştur** (systemic pattern için):
   ```
   docs/ai/ADRs/NNNN-<title>.md
   ```
   Format: Nygard ADR (context/decision/consequences)
5. **Anti-pattern katalog** güncelle: `docs/ai/anti-patterns.md`
6. **Değişiklik özeti** (haftalık):
   ```
   docs/ai/knowledge-updates/YYYY-WW.md
   ```
7. Commit:
   ```bash
   git checkout test && git pull && git checkout -b knowledge/week-YYYY-WW
   git add docs/ai/GROUNDING.md docs/ai/ADRs/ docs/ai/anti-patterns.md docs/ai/knowledge-updates/
   git commit -m "docs: knowledge update YYYY-WW [pipeline: knowledge_curator]" --no-verify
   git push -u origin knowledge/week-YYYY-WW
   gh pr create --base test --title "docs: bilgi güncellemesi — hafta YYYY-WW"
   ```

---

## Output

- Güncel `GROUNDING.md`
- Yeni ADR'ler (varsa)
- Weekly knowledge update notu
- PR `test`'e

---

## Done kriteri

- ✅ Yeni retroların her biri GROUNDING ihtimaline bakıldı
- ✅ 3+ tekrarlayan pattern ADR oldu
- ✅ Çelişkili kurallar çözüldü
- ✅ Eskimiş bölümler işaretlendi

---

## Yasaklar

1. Tek retro'dan ADR yazma (pattern için 3+ sinyal)
2. GROUNDING'i "temizlemek" adına önemli convention silme
3. Geriye dönük çakışmaları görmezden gelme
4. Haftalık update'i atlama (pattern birikirse iş katlanır)

---

## Handoff

Sonraki pipeline item'lar güncellenmiş GROUNDING'i okuyacak. Döngü böyle kapanır.
