# Gap Analysis — GAP-001

> **Title:** Sidebar navigasyonunda klavye kullanıcısı menüye erişemiyor (WCAG 2.1 AA ihlali)  
> **Type:** GAP  
> **Priority:** medium  
> **Scope:** fe  
> **Found by:** analyzer-{{agent_id}} on {{date}}

---

## Özet (1-2 cümle)

Sidebar navigasyonunda klavye kullanıcıları menüye erişemiyor. Bu durum WCAG 2.1 AA standardına göre bir ihlaldir.

---

## Kanıt

### Dosya referansları

```
apps/web/src/components/Nav.ts:10-20
docs/a11y/sidebars/keyboard-nav.html:30-40
```

### Reproducible adımlar

```bash
# Bulguyu nasıl teyit ederim:
$ cd apps/web
$ npm run test:a11y -- --url=/dashboard
# Expected: pass
# Actual: 14 violations, including ...
```

---

## Etki

- **Kullanıcı:** Klavye kullanıcıları etkileniyor.
- **Teknik:** Bu durum code health ve a11y anlamında bir risk oluşturuyor.
- **Öncelik gerekçesi:** Kullanıcı deneyimi için bu ihlal kritik.

---

## Kapsam sınırı

Bu gap içinde olmayan şeyler:
- ...
- ...

---

## Referans

- Standart/kural: WCAG 2.1 AA
- İlgili diğer gap'ler: GAP-002, GAP-003
- Benzer past issues: https://github.com/ourproject/past-issues/issues/123

---

[pipeline: analyzer GAP-001]

```json
{
  "decision": "approve",
  "confidence": 0.9,
  "reason": "Bulunan ihlal WCAG 2.1 AA standardına göre bir ihlaldir ve kullanıcı deneyimi için kritik bir risk oluşturuyor."
}
```

Note: The JSON block at the end is added as per the decision role requirements.
