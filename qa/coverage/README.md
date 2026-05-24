# coverage/

**Bu klasörün tüm dosyaları `qa/tools/trace.mjs` tarafından otomatik üretilir.**

Manuel düzenleme yapma — bir sonraki `trace.mjs` çalışmasında üzerine yazılır.

## Dosyalar

| Dosya | İçerik | Üretici |
|---|---|---|
| `traceability.csv` | TC × otomasyon × requirement × last_run × open_defects matrisi | `trace.mjs` |
| `coverage-matrix.md` | Suite × priority pivot tablosu (P0/P1/P2/P3 + automation%) | `trace.mjs` |
| `orphans.md` | Boşluklar: tagged-but-missing-TC, automated-but-not-tagged, TC-without-requirement, REQ-without-TC | `trace.mjs` |

## Çalıştırma

```bash
# Üret veya güncelle
npm run trace

# CI: sadece doğrula (üretmez, fark varsa exit 1)
node tools/trace.mjs --check
```

## CI'da çalışması

`.github/workflows/qa-validate.yml` her PR'da `trace.mjs --check` çalıştırır. Eğer çıktı dosyaları stale ise (yani TC eklendi/silindi ama bu klasör güncellenmedi) workflow fail eder. Bu durumda lokalde `npm run trace && git add qa/coverage && git commit` ile güncelle.

## Niye git'te tutuluyor?

İki sebep:
1. **External stakeholder erişimi**: GitHub UI'dan `traceability.csv`'yi açıp filtreleyebilirler, repo'yu çekmek zorunda değiller
2. **Tarihsel snapshot**: 6 ay sonra "Q2 release sırasında coverage neydi?" sorusunun cevabı git history'de
