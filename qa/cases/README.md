# cases/

Test case'ler. Her domain bir klasör, her TC bir `.md` dosyası.

## Klasör yapısı

```
cases/
├── auth/
│   ├── _suite.yml
│   ├── TC-AUTH-001-basarili-login.md
│   ├── TC-AUTH-002-hatali-parola.md
│   └── _draft/                          ← AI üretti, henüz review edilmedi
│       └── DRAFT-TC-AUTH-018-mfa.md
├── projects/
├── scenarios/
└── ...
```

## Yeni TC ekleme

```bash
npm run new-tc -- --suite=auth --title="MFA login akışı"
```

Manuel ekleyeceksen `templates/test-case.template.md`'yi kopyala.

## Suite ekleme

1. Yeni klasör: `mkdir cases/yeni-suite`
2. `_suite.yml`: `templates/suite.template.yml`'den kopyala
3. `tools/lib/domains.mjs`'e suite → domain prefix eşlemesi ekle
4. `CONVENTIONS.md`'deki domain tablosunu güncelle
5. PR aç

## Draft TC'ler

`_draft/` klasörü AI ile üretilen taslakları tutar. Bunlar:
- **Active TC değildir** (filename `DRAFT-` prefix'li)
- `validate.mjs` taraflarından tolerans gösterilir (warn, fail değil)
- Human review sonrası promote edilir: filename'i `DRAFT-` prefix'inden temizle + frontmatter `status: draft` → `active`
