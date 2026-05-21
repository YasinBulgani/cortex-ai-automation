# Code Review — {{ID}} ({{SCOPE}})

> **By:** code-reviewer-{{agent_id}} on {{date}}  
> **Target PR:** #{{PR}}  
> **Decision:** **approve** ✅ | **request-changes** ⚠️

---

## Güçlü yönler

- <ne iyi yapıldı>
- <iyi decision>

---

## Bloklayıcı bulgular (must-fix)

<yoksa: **none** — approve için şart. Varsa her biri için:>

### BF-1: <kısa başlık>
- **Path:** `path/to/file.ts:42-58`
- **Problem:** <ne yanlış>
- **Öneri:** <somut düzeltme>
- **Gerekçe:** <neden blocker>

---

## Öneriler (nice-to-have)

- `path/to/file.ts:X` — <öneri, refactor fikri>
- ...

---

## Kontrol listesi

### Kod kalitesi
- [ ] Naming tutarlı + anlamlı
- [ ] Duplication yok (DRY)
- [ ] Fonksiyonlar 50 satırın altında
- [ ] Separation of concerns (router/service/data)

### Test coverage
- [ ] Yeni kod için unit test var
- [ ] Critical path için integration/e2e test
- [ ] Edge case testleri (null, empty, boundary)

### Type safety (TS)
- [ ] `any` kullanımı yok (veya gerekçelendirilmiş)
- [ ] Implicit any yok
- [ ] Unchecked array index yok

### Security red flags
- [ ] Hardcoded secret yok
- [ ] SQL string concat yok (param binding)
- [ ] User input sanitize
- [ ] Log'larda sensitive data yok
- [ ] Auth guard her endpoint'te

### Design system / convention (FE)
- [ ] Mevcut component'ler tercih edildi
- [ ] Design token'ları kullanıldı (ad-hoc style yok)
- [ ] `data-testid` convention uygulandı
- [ ] i18n string literal yok (t() kullanıldı)

### Performance
- [ ] N+1 query yok
- [ ] Gereksiz re-render yok (memo/useMemo uygun)
- [ ] Bundle impact minimal

### Documentation
- [ ] Public API için JSDoc/docstring
- [ ] Breaking change varsa migration note
- [ ] Complex logic için açıklama

---

## Verdict

**approve** — integrator açılabilir.

(veya **request-changes** — BF-N düzeltilmeli, loop-back fe/be)

---

[pipeline: code_reviewer {{ID}} {{SCOPE}}]
