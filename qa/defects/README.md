# defects/

**GitHub Issues mirror'ı.** Kanonik kaynak GitHub Issues, bu klasör sadece **closed defect'lerin** snapshot'ı.

## Niye?

1. **AI training data**: Defect ↔ TC ↔ failure pattern eşleşmesi LLM için değerli
2. **Audit history**: 5 yıl sonra "bu bug nasıl çözüldü?" sorusunun cevabı git'te
3. **Coverage analizi**: `trace.mjs` open defect'leri TC'lere bağlar

## Kanonik akış

```
Failed run (runs/.../TR-*.yml)
       │
       │ run-record.mjs / import-results.mjs
       ▼
GitHub Issue oluşturulur (örn. #1234)
       │ workflow: triage, assignment, fix, verify, close
       ▼
Issue closed → CI bot mirror oluşturur
       │
       ▼
defects/GH-1234.md (closed snapshot)
```

## Manuel ekleme

Şimdilik (mirror automation PR 4+'a kadar) manuel: `templates/defect.template.md`'den kopyala.

## ID şeması

`GH-{NUMBER}` — GitHub Issue numarası direkt. Lokal `DEF-*` ID'si **yoktur**.

## Açık defect'lere referans

TC frontmatter'ında:

```yaml
open_defects: [GH-1234, GH-1567]
```

Bu external Issue ID'lerine işaret eder. Issue kapanınca `defects/GH-1234.md` oluşur ve TC'den ref kaldırılır (yeni TC versiyonu açılır veya frontmatter güncellenir).
