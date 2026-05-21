# Gap Analysis — {{ID}}

> **Title:** {{TITLE}}  
> **Type:** GAP  
> **Priority:** {low | medium | high | critical}  
> **Scope:** {fe | be | fullstack | infra | test | docs}  
> **Found by:** analyzer-{{agent_id}} on {{date}}

---

## Özet (1-2 cümle)

<Bulgunun kısa tanımı, non-teknik okuyucu da anlasın>

---

## Kanıt

### Dosya referansları

```
<path/to/file.ts:LINE_START-LINE_END>
<path/to/other.py:LINE>
```

### Reproducible adımlar

```bash
# Bulguyu nasıl teyit ederim:
$ cd apps/web
$ npm run test:a11y -- --url=/dashboard
# Expected: pass
# Actual: 14 violations, including ...
```

### Screenshot / log (varsa)

`docs/ai/pipeline/items/{{ID}}/evidence/` altına eklendi:
- `axe-report.json`
- `before.png`

---

## Etki

- **Kullanıcı:** <kimi nasıl etkiliyor>
- **Teknik:** <code health, perf, security anlamında etkisi>
- **Öncelik gerekçesi:** <neden {{priority}}?>

---

## Kapsam sınırı

Bu gap içinde **olmayan** şeyler (scope creep engellemek için):
- ...
- ...

---

## Referans

- Standart/kural: <WCAG 2.1 AA / OWASP A01 / RFC 7231 / vs.>
- İlgili diğer gap'ler: <GAP-XXX, GAP-YYY>
- Benzer past issues: <link>

---

[pipeline: analyzer {{ID}}]
