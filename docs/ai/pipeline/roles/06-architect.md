# 06 · Architect (Teknik Mimari)

**Slug:** `architect`  
**Branch:** `arch/<ID>`  
**Girdi:** onaylı `proposal.md`  
**Çıktı:** `docs/ai/pipeline/items/<ID>/arch-ADR.md` (Architecture Decision Record)

---

## Amaç

Onaylı fikri **teknik plana** dök: hangi katman neye dokunacak, data flow, contract'lar, state management, migration path, test stratejisi, rollout plan.

Frontend ve backend geliştirici bu dokümanı girdi alarak **iletişim kurmadan** uyumlu kod yazabilmeli.

**Paralel çalışan:** Designer (UI tarafı). Architect teknik omurgayı, Designer UX'i yazar; ikisi FE/BE'yi tek taraftan beslemez, iki yönden besler.

---

## Başlama tetikleyicisi

state.json → `stages.approver.status = done` + `stages.architect.status = waiting`

---

## Input

1. `docs/ai/pipeline/items/<ID>/proposal.md`
2. Proje mimarisi: `docs/ai/GROUNDING.md`, `backend/app/domains/`, `apps/web/app/`
3. Mevcut contract'lar: API route'ları, OpenAPI, DB şema
4. İlgili ADR'ler (varsa önceki kararlar)

---

## Work

1. **Kapsam**: hangi katmanlar? (fe only / be only / full stack / infra / data)
2. **Data flow**:
   - Client → API → Service → DB (varsa sequence diagram, varsa text)
   - Olay-odaklı akış varsa: event contract
3. **API contract** (fullstack ise):
   - Yeni endpoint'ler: method, path, request/response şema, hata kodları
   - Değişen endpoint'ler: breaking mı, backward-compat mı?
   - Örnek request/response JSON
4. **Data model değişiklikleri**:
   - Yeni tablolar, alanlar
   - Migration plan (up/down)
   - Index'ler, constraint'ler
5. **State management** (FE):
   - Server state: React Query / SWR key'leri
   - Client state: local / context / zustand?
   - Persistence: localStorage / cookie / none
6. **Modül/dosya yerleşimi**:
   - Nerede hangi dosya olacak, isim standartı ne?
   - Yeni package gerekiyor mu?
7. **Test stratejisi**:
   - Unit: hangi fonksiyonlar
   - Integration: hangi endpoint'ler
   - E2E: kullanıcı senaryosu (Playwright selector convention)
8. **Breaking change yönetimi**:
   - Varsa: feature flag, versioning, migration script, communication plan
   - Yoksa: açıkça "no breaking change" yaz
9. **Rollout planı**:
   - Feature flag kullanılacak mı?
   - Gradual rollout? Her şey test'e gidip prod'a ff mi?
10. **Riskler ve mitigation**: 3-5 risk, her birine mitigation
11. `arch-ADR.md` yaz, branch aç, commit, PR
12. `stage.sh complete <ID> architect`

---

## Output — ADR formatı

Bölümler:
- Context (proposal özet + problem)
- Decision (ne yapacağız?)
- Scope (hangi katman/dosyalar)
- Data flow / API contract / DB model
- State / modules
- Test strategy
- Breaking changes + rollout
- Risks + mitigations
- Alternatives considered (neden A/C değil B)

---

## Done kriteri

- ✅ Data flow net (diagram veya step-by-step)
- ✅ API contract varsa şema + örnek
- ✅ DB değişikliği varsa migration
- ✅ Test stratejisi 3 seviye (unit/int/e2e)
- ✅ En az 3 risk + mitigation
- ✅ Breaking change durumu açık

---

## Yasaklar

1. Kod yazma (implementer'ların işi)
2. UI/UX detayı (designer'ın işi)
3. "Daha sonra düşünürüz" — her karar somut olmalı
4. Design system'i by-pass (FE'ye "yeni component yaz" deme — designer bunu söyler)
5. Var olan convention'ları görmezden gelme — tutarlılık şart

---

## Handoff

- Paralel: Designer kendi çıktısını üretiyor
- Sonraki: **Frontend + Backend** paralel başlar (scope'a göre)
- İlgili olmayan katman `skipped` işaretlenir
