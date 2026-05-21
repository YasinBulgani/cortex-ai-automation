# 07 · Frontend (FE Implementasyon)

**Slug:** `frontend`  
**Branch:** `feat/fe-<ID>`  
**Girdi:** `design.md` + `arch-ADR.md`  
**Çıktı:** FE kodu + FE testleri, PR `test`'e

---

## Amaç

Designer'ın ve architect'in dokümanlarını **çalışan React/Next.js koduna** çevir. Var olan design system'e uyarak, a11y ve i18n gereksinimlerini atlamadan.

**Paralel çalışan:** Backend (eğer scope fullstack ise). FE backend'e contract üzerinden güvenir; contract henüz hazır değilse mock'la ilerler.

---

## Başlama tetikleyicisi

state.json → `stages.designer.status = done` + `stages.architect.status = done` + `stages.frontend.status = waiting`

**Skip durumu:** Arch-ADR "fe scope yok" dediyse `stages.frontend.status = skipped` ve direkt integrator'a geçilir.

---

## Input

1. `docs/ai/pipeline/items/<ID>/design.md` — UI/UX spec
2. `docs/ai/pipeline/items/<ID>/arch-ADR.md` — teknik karar
3. `apps/web/` mevcut kod yapısı
4. `.cursor/rules/data-testid-convention.mdc`
5. `.cursor/rules/page-object-pattern.mdc`
6. `apps/web/components/ui/` mevcut bileşenler

---

## Work

1. **Branch aç**:
   ```bash
   git checkout test && git pull && git checkout -b feat/fe-<ID>
   ```
2. **Dosya yerleşimi**: arch-ADR'nin dediği yere, isim standardına uygun
3. **Implementation**:
   - Designer'ın envanterindeki her bileşeni oluştur/kullan
   - State management: arch-ADR'nin dediği gibi (React Query, context, vs.)
   - API çağrıları: arch-ADR'deki contract'a göre
   - Her etkileşim için `data-testid` (convention'a uy)
4. **A11y implementasyon**:
   - Designer'ın checklist'indeki her madde
   - Keyboard nav, ARIA, focus management
   - Reduced-motion: `prefers-reduced-motion`
5. **i18n**: user-facing string'ler `t()` ile, mesaj dosyasına ekle
6. **Responsive**: designer'ın 3 breakpoint planı
7. **Tipe uyum**: `tsc --noEmit` sıfır hata
8. **Testler**:
   - Unit: react-testing-library (state, props, etkileşim)
   - E2E selector: data-testid ile, `e2e/` altına test
9. **Lint + format**: `npm run lint && npm run format`
10. **Commit stratejisi** (açık path):
    ```bash
    git reset HEAD
    git add apps/web/components/.../ apps/web/app/.../ e2e/.../
    git commit -m "feat(fe): <ID> — <başlık> [pipeline: frontend <ID>]" --no-verify
    git show --stat HEAD   # doğrula
    ```
11. Push + PR:
    ```bash
    git push -u origin feat/fe-<ID>
    gh pr create --base test --title "feat(fe): <başlık> [<ID>]" --body "..."
    ```
12. `stage.sh complete <ID> frontend`

---

## Mock-first mode (backend paralel ve henüz contract yoksa)

Architect contract'ı yazdıysa kesin oraya uy. Hazır değilse:
1. `apps/web/lib/api/` altında mock service yaz
2. MSW veya basit fetch wrapper ile mock'la
3. Integration için `.env.local` flag: `USE_MOCK=1`
4. Backend commit'i geldikten sonra entegrator mock'u gerçeğiyle değiştirir

---

## Done kriteri

- ✅ tsc: 0 hata
- ✅ lint: 0 error (warning tolere)
- ✅ Unit test'ler yeşil
- ✅ data-testid convention uygulandı
- ✅ A11y checklist işlendi (designer listesi)
- ✅ i18n string'leri eklendi
- ✅ Responsive 3 breakpoint'te çalışıyor (manuel kontrol)
- ✅ PR `test`'e açık, description'da design/arch linkleri

---

## Yasaklar

1. Design system dışı ad-hoc style
2. `any` type (gerekiyorsa `unknown` + narrow)
3. `data-testid` atlama (e2e test kırılır)
4. i18n atlama (hardcoded Türkçe/İngilizce string)
5. Arch-ADR'deki contract'tan sapma (sapmak istiyorsan PR'da architect'i mention et, önce tartış)
6. `git add .` / `-A` / `commit -a`

---

## Handoff

- Backend paralel çalışıyor olabilir — ikisi de bitince **Integrator** devreye girer
- Integrator FE+BE branch'lerini birleştirir, contract uyumsuzluklarını bulursa FE'ye geri gönderir
