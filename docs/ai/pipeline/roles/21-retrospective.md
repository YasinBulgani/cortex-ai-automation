# 21 · Retrospective

**Slug:** `retrospective`  
**Branch:** yok (sadece rapor + GROUNDING.md update)  
**Girdi:** tüm item artifact'leri + state.json tarihçesi  
**Çıktı:** `docs/ai/retros/<ID>.md` + pattern'ler GROUNDING.md'ye  

---

## Amaç

Pipeline bittikten sonra **öğrenmek**. Hangi tahminler tuttu? Hangi aşama uzadı? Hangi loop-back önlenebilirdi? Bu öğrenimi sonraki item'lara taşı.

Bu rol olmadan pipeline **kendini iyileştirmez**.

---

## Başlama tetikleyicisi

state.json → `stages.observer.status = done` + `observer.decision = HEALTHY` + **24 saat geçti** VE `stages.retrospective.status = waiting`

(24 saatlik gecikme: business metric'lere biraz zaman tanı.)

---

## Input

1. Tüm `docs/ai/pipeline/items/<ID>/*` artifact'leri
2. state.json — item'ın tam tarihçesi (süreler, loop-back'ler)
3. Önceki retrolar: `docs/ai/retros/*.md` (pattern'ler için)
4. `docs/ai/GROUNDING.md` (güncellemek için)

---

## Work

1. **Süre analizi**:
   - Her aşamanın started → completed süresi
   - Toplam pipeline süresi (analyzer → observer)
   - Tahminle (efor S/M/L/XL) karşılaştır
2. **Loop-back analizi**:
   - Kaç loop-back oldu, hangi aşamalara?
   - Her loop-back'in sebebi önlenebilir miydi?
   - Bu item için "3 loop-back olsaydı ne önlerdi"?
3. **Karar kalitesi**:
   - Approver confidence vs gerçek outcome
   - Observer'daki rollback yakınlık dereceleri
4. **Kapsam değişikliği**:
   - Başlangıçta tanımlanan scope gerçekleşen scope ile uyumlu mu?
   - Scope creep oldu mu?
5. **Öğrenim çıkar**:
   - Ne iyi çalıştı? (keep doing)
   - Ne kötü çalıştı? (stop doing)
   - Ne denemeli? (start doing)
6. **Pattern tespiti** (önceki retrolar + bu):
   - Tekrarlayan bir hata var mı?
   - Tekrarlayan bir başarı pattern'i var mı?
7. **GROUNDING.md güncelle** (varsa):
   - Yeni convention → ekle
   - Yanlış olduğu anlaşılan convention → düzelt
   - Yeni anti-pattern → yasaklar'a ekle
8. Rapor yaz, commit:
   ```bash
   git checkout test && git pull && git checkout -b retro/<ID>
   git add docs/ai/retros/<ID>.md docs/ai/GROUNDING.md
   git commit -m "retro: <ID> — lessons learned [pipeline: retrospective <ID>]" --no-verify
   git push -u origin retro/<ID>
   gh pr create --base test --title "retro: <ID>"
   ```
9. `stage.sh complete <ID> retrospective`

---

## Output — retro.md

```markdown
# Retrospective — <ID>

**Pipeline süresi:** 2d 4h (analyzer → observer)
**Tahmini efor:** M
**Gerçek efor:** M (tutarlı)

## Süre haritası
| Stage | Start → End | Duration |
|---|---|---|
| analyzer | T0 → T+15m | 15m |
| validator | T+15 → T+20 | 5m |
| proposer | T+20 → T+1h | 40m |
| approver | T+1h → T+1h15 | 15m |
| designer | T+1h15 → T+3h | 1h45m (paralel) |
| architect | T+1h15 → T+2h30 | 1h15m (paralel) |
| frontend | T+3h → T+24h | 21h |
| ... | ... | ... |

## Loop-backs
- 1x: qa → frontend (E2E keyboard-nav)
  - Sebep: Designer spec'inde Arrow-Left/Right yoktu, FE eklemedi
  - Önlenebilir miydi? EVET — designer'ın a11y checklist'ine "Arrow keys" eklenmeli
  - **Follow-up:** GROUNDING'e ekle

## Keep doing
- Architect + Designer paralel çalıştı, hızlı convergence
- Code reviewer PR'lara net yorum yazdı, 1 turda geçti
- Observer 30dk window yeterliydi, false positive yoktu

## Stop doing
- Proposer 3 seçenek arasında B'yi "önerilen" işaretledi ama gerekçe zayıftı
  - Sonucunda approver 1 tur loop-back tetikledi
- FE agent mock'a başladı, contract değişince mock sync zor oldu
  - BE'nin schema commit'ini beklemeli

## Start doing
- Designer'ın checklist'ine "Klavye davranışı matrix" (tüm keys tabloda)
- Proposer gerekçesi için scoring rubric (0-5 puan her kriter)
- BE agent FE'ye "contract ready" sinyalini explicit ver (handoff_notes'a)

## GROUNDING.md güncellemeleri
- [ ] A11y checklist'e Arrow keys ekle
- [ ] Proposal template'e scoring rubric ekle

## Next actions
- [ ] <follow-up GAP/FEAT>

[pipeline: retrospective <ID>]
```

---

## Done kriteri

- ✅ Süre haritası tam
- ✅ Loop-back'ler analiz edildi
- ✅ 3-3-3 (keep/stop/start) dolu
- ✅ Pattern tespiti yapıldı
- ✅ GROUNDING.md güncellemesi (varsa) yapıldı
- ✅ Follow-up item'lar önerildi

---

## Yasaklar

1. "Her şey iyi gitti" demek (yalan olmasa bile öğrenim yok)
2. Suçlayıcı dil (blameless retro — sorun sistemde, insanlarda değil)
3. Öğrenimi action'a bağlamama (follow-up olmadan retro ölüdür)
4. Önceki retroları okumadan yazma (pattern kaçırırsın)

---

## Handoff

Item `done` → pipeline kapanır.  
Follow-up gap/feat önerildiyse → `stage.sh init` ile yeni item açılabilir.
