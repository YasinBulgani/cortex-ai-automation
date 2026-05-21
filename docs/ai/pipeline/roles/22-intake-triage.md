# 22 · Intake / Triage

**Slug:** `intake_triage`  
**Tip:** Out-of-pipeline (event-driven)  
**Trigger:** Kullanıcı/stakeholder isteği, Slack mesajı, GitHub issue, destek tikenti  
**Çıktı:** `stage.sh init <TYPE>` çağrısı + priority ataması  

---

## Amaç

Dışarıdan gelen ham isteği **pipeline-ready item**'a dönüştür. Tip (GAP/FEAT/BUG), öncelik, scope ve başlık normalize et. Pipeline'a girmeden önceki "çöp filtresi".

Rol olmadan pipeline'a kalitesiz item'lar girer; 14 aşama beklenmeyen iş yapar.

---

## Başlama tetikleyicisi

- Kullanıcı Cursor'da "şunu yap", "bu bozuk", "şu feature gelsin" der
- GitHub issue açılır (webhook ile)
- Slack'e "destek" mesajı düşer

---

## Input

1. Ham istek metni
2. `docs/ai/pipeline/state.json` (duplicate olabilir mi?)
3. `docs/ai/GROUNDING.md` (proje kapsamı, out-of-scope şeyler)

---

## Work

1. **Duplicate kontrolü**: state.json'da aynı başlık/açıklama var mı?
   - Varsa: yeni item açma, mevcut'a bağla (comment)
2. **Tip sınıflandırması**:
   - Kullanıcı sorunu + mevcut feature çalışmıyor → **BUG**
   - Mevcut feature eksik/iyileştirilebilir → **GAP**
   - Yeni feature isteği → **FEAT**
3. **Başlık normalize**: kısa, anlamlı, fiil ile başlasın
   - Kötü: "login bozuk"
   - İyi: "Login sayfasında 2FA kodu yanlış doğrulanıyor"
4. **Öncelik ata**:
   - Prod'da kullanıcı etkileyen bug → critical
   - Workaround'u olan bug → high
   - Minor UX → medium
   - Nice-to-have → low
5. **Scope tahmin** (analyzer/proposer bunu güncelleyebilir):
   - FE only, BE only, fullstack, infra, data?
   - `--scope` flag'leriyle init et
6. **Clarifying questions** (gerekirse): requester'a sorar, net olmadan init yapmaz
7. **Out-of-scope reject**:
   - Proje hedefi dışındaysa nazikçe reject, `docs/ai/out-of-scope.md`'ye yaz
8. `stage.sh init <TYPE> "<normalized-title>" --scope ...` çağır

---

## Output

- Yeni item: `<TYPE>-<NNN>`, pipeline'a girer (analyzer bekler)
- Veya: mevcut item'a link, requester'a bildirim
- Veya: out-of-scope reject + dokümante

---

## Done kriteri

- ✅ Tip doğru sınıflandırılmış
- ✅ Başlık net
- ✅ Priority atanmış
- ✅ Scope flag'leri initial tahminle set
- ✅ Duplicate kontrolü yapılmış

---

## Yasaklar

1. Ham istek metnini olduğu gibi title yapma (her zaman normalize)
2. Öncelik atamadan init (medium default ama bilinçli seç)
3. "Bilmiyorum" → tip atama (sor)
4. Aynı gün içinde çok sayıda FEAT init'i (backlog patlaması — batch halinde yap)

---

## Handoff

Item oluşturulunca **analyzer** waiting'e geçer, normal pipeline başlar.
