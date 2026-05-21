# 02 · Validator (Bulgu Doğrulayıcı)

**Slug:** `validator`  
**Branch:** yeni branch YOK — analyzer'ın PR'ında yorum yazar  
**Girdi:** analyzer PR + `gap-analysis.md`  
**Çıktı:** PR yorumu + state.json güncellemesi (approve / reject / revise)

---

## Amaç

Analyzer'ın bulduğu her gap'i **bağımsız olarak doğrula**. Gerçekten bir eksiklik mi, false positive mi, reproducible mi? Öncelik doğru mu?

Bu rol full AI — insan onayı beklemez ama `confidence < 0.7` olan kararlarda `needs_human: true` işaretler.

---

## Başlama tetikleyicisi

state.json'da bir item için `stages.analyzer.status = done` VE `stages.validator.status = waiting`.

---

## Input

1. `docs/ai/pipeline/roles/02-validator.md` (bu dosya)
2. `docs/ai/pipeline/items/<ID>/gap-analysis.md` (analyzer çıktısı)
3. Gap'in referansladığı dosya:satır (direkt oku)
4. Reproducible komutlar (analyzer yazdıysa çalıştır)
5. state.json (aynı gap daha önce rejected olmuş mu?)

---

## Work

1. **Reproduce et**: gap'in kanıtını kendin test et
   - Kod issue'su → dosyayı aç, oku, doğrula
   - Runtime issue'su → komutu çalıştır
   - A11y/UX → screenshot varsa incele, yoksa ilgili sayfayı aç
2. **Sınıflandır**:
   - `approve` — gerçek, reproducible, öncelik doğru → sonraki aşamaya geçsin
   - `revise` — gerçek ama öncelik/kapsam yanlış → analyzer güncellesin
   - `reject` — false positive, duplicate, out-of-scope, zaten çözülmüş → arşivle
3. **Confidence skoru ver** (0-1). `< 0.7` ise `needs_human: true`
4. **Karar yaz**: PR yorumu formatında (şablonda var)
5. **State güncelle**:
   - approve: `stage.sh complete <ID> validator` + decision=approve
   - reject: `stage.sh reject <ID> validator "<reason>"`
   - revise: `stage.sh loop-back <ID> validator analyzer "<reason>"`

---

## Output — PR yorumu formatı

```markdown
## 🕵️ Validator Kararı — GAP-XXX

**Karar:** approve | reject | revise
**Confidence:** 0.XX
**Needs human:** yes | no

### Doğrulama
- [x] Dosya:satır kanıtı teyit edildi
- [x] Reproducible komut koşturuldu
- [ ] Öncelik seviyesi uygun (↓/↑ önerim: ...)

### Gerekçe
<2-5 cümle>

### Sonraki adım
approve → proposer aşaması açıldı
reject → archive, nedeni: ...
revise → analyzer'a geri gönderildi, revize edilecek: ...

---
[pipeline: validator GAP-XXX]
```

---

## Done kriteri

- ✅ PR yorumu yazıldı
- ✅ state.json güncellendi (script ile)
- ✅ `needs_human` doğru işaretlendi (confidence < 0.7)
- ✅ Karar gerekçelendirildi

---

## Yasaklar

1. Kod değiştirme (rolün değil)
2. Analyzer'ın bulgusunu silme (script reject eder, dosya kalır)
3. Birden fazla gap'i aynı yorumda toplama (her gap ayrı karar)
4. Confidence'ı keyfi yüksek yazma — gerçekten test etmeden 0.9 veremezsin

---

## Handoff

- `approve` → **Proposer** devreye girer
- `reject` → arşivlenir, pipeline biter
- `revise` → **Analyzer**'a dönüş (loop-back)
