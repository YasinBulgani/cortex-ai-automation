# Web Route Onboarding Checklist

Bu dokuman `apps/web/app/(dashboard)/p/[projectId]/...` altina yeni bir sayfa eklerken route, navigasyon ve yetki tutarliligini korumak icin kullanilir.

## 1) Route olusturma

- Yeni segment icin `app/(dashboard)/p/[projectId]/<segment>/page.tsx` ekle.
- Sayfa API cagrilari icin `apiFetch` kullan ve `fetch` cagrilarinda tekil davranis olusturmaktan kacin.
- Yukleme/hata/bos durumlarini gorunur kil (skeleton veya bilgi karti).

## 2) Navigasyon esleme

- `apps/web/lib/product.ts` icinde `PROJECT_NAV_DEFINITIONS` listesine route kaydi ekle.
- `segment` ile gercek klasor adinin birebir uyumlu oldugunu dogrula.
- Gerekli urun ailesi filtreleri (`productIds`) ve grup (`group`) alanlarini belirle.

## 3) Shell ve menu dogrulama

- `apps/web/components/AppShell.tsx` icinde yeni route'un menu akisinda gorunurlugunu dogrula.
- Route gorunur ama sayfa yok / sayfa var ama menu yok drift'ini engellemek icin smoke test ekle.

## 4) Yetki ve auth

- Backend endpointlerinde `Depends(get_current_user)` ve gerekiyorsa izin kontrolu oldugunu dogrula.
- Frontend tarafinda auth akisi icin middleware yonlendirmesini (`apps/web/middleware.ts`) bozmadigindan emin ol.

## 5) Test ve dokumantasyon

- En az bir e2e navigasyon veya API smoke testi ekle.
- Gerekirse `docs/MASTER.md` icine yeni route ailesini veya yeni is akisina ait referansi ekle.
