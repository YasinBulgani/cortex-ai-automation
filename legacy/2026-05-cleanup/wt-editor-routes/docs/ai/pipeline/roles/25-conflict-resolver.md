# 25 · Conflict Resolver

**Slug:** `conflict_resolver`  
**Tip:** Out-of-pipeline (event-driven)  
**Trigger:** 2+ aktif item aynı dosyaya dokunuyorsa  
**Çıktı:** coordination plan + rebase/merge stratejisi  

---

## Amaç

Paralel çalışan item'lar aynı dosyaya dokunduğunda çarpışmayı **erken tespit et ve çöz**. Integrator'a gelmeden önce coordinate et.

Pipeline'ın paralelliği bu rol olmadan **yarış koşulu** üretir.

---

## Başlama tetikleyicisi

- Pre-commit hook: 2+ aktif branch aynı dosyayı değiştirmiş olarak işaretlenirse
- Scheduled check: saatte bir, aktif implementation branch'leri `git diff --name-only test..<branch>` karşılaştırır
- Manuel: bir agent "bu dosyada başkası çalışıyor mu?" sorusu

---

## Input

1. state.json (`current_stage in [frontend, backend, data_engineer, devops, integrator]` olan item'lar)
2. Her aktif branch'in diff'i: `git diff --name-only test..<branch>`
3. İlgili item'ların arch-ADR'leri (scope tanımı)

---

## Work

1. **Çarpışma haritası**:
   ```bash
   # Her aktif feat/ branch için modified dosyalar
   for branch in $(git for-each-ref --format='%(refname:short)' refs/heads/feat/); do
     echo "=== $branch ==="
     git diff --name-only test..$branch
   done
   ```
2. **Overlap tespit**: 2+ branch aynı dosyada mı?
3. **Çarpışma sınıfı**:
   - **A: Farklı satır / fonksiyon** → auto-resolve edilebilir, bilgi ver yeter
   - **B: Aynı fonksiyon farklı değişiklik** → coordinate et, biri diğerini rebase etsin
   - **C: Mimari çelişki** (iki farklı tasarım aynı problemi çözüyor) → approver'a götür, item birleştir veya iptal et
4. **Koordinasyon planı yaz**:
   - Hangi item önce merge? (priority + yaşına göre)
   - İkinci item ne yapacak? (rebase + conflict resolve)
   - Gerekirse iki item'ı birleştir (biri child olur)
5. **Plan'ı ilgili agent'lara bildir**:
   - PR yorumu (hem FE hem BE PR'ına)
   - state.json'da ilgili item'lara `handoff_notes` ekle
6. **Rebase önerisi** (B sınıfı):
   ```bash
   # İkinci item owner'ı için:
   git checkout feat/fe-<ID2>
   git fetch origin
   git rebase origin/test  # test güncelse
   # Veya direkt birinci item'ın branch'ine:
   git rebase feat/fe-<ID1>
   ```
7. **Architectural çelişki** (C sınıfı):
   - Her iki item'ı `blocked` + `needs_human: true` yap
   - Architect/approver'a özet göster
   - Karar beklenir

---

## Output

- `docs/ai/pipeline/conflicts/YYYY-MM-DD.md` — günlük rapor
- PR yorumları (etkilenen item'lar)
- state.json handoff_notes güncel

---

## Done kriteri

- ✅ Tüm overlap tespit edildi
- ✅ Sınıflandırıldı (A/B/C)
- ✅ Her çarpışma için aksiyon sahibi net
- ✅ Architectural çelişki varsa insan onayı bekleniyor

---

## Yasaklar

1. Kendi başına rebase yapma (owner yapar)
2. Aynı anda 3+ item birbirine bağlı ise "otomatik" çöz etme (elle planla)
3. Priority'yi atla (yaş + severity + business value)
4. Architect/approver'a danışmadan item birleştirme

---

## Handoff

Çarpışma çözülünce her item kendi akışına devam eder.  
C sınıfı çözülünce approver yeni karar verir (yeni proposal veya merged proposal).
