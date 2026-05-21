# docs/history — Arşiv

Bu klasör geçmiş sürüm dokümanlarını, eski planları ve sunumları tutar.
Güncel bilgi için repo kökündeki [README.md](../../README.md) ve `docs/`
dizinindeki resmi belgelere bakınız.

Buradaki dosyalar referans amaçlıdır; üretim veya süreç kararları için
doğrudan kaynak alınmamalıdır.

## İçerik

- `AKIS_HARITASI.md`, `MERGER_PLAN.md`, `DESIGN_UPGRADE_PLAN.md`,
  `PROGRESS.md`, `COMPLETION_REPORT.md`, `DEPLOYMENT_CHECKLIST.md`,
  `PROJE_TEMIZLIK_RAPORU.md`: Farklı sprintlerde üretilmiş rapor ve
  planlar. Güncel tekil kaynak: kök `README.md` ve `docs/adr/`.
- `BGTS_Master_Plan.html`, `BGTS_Uygulama_Plani.html`,
  `Cockpit_QA_Test_Sunum.pptx`: Paydaşlara gösterilen eski sunumlar.
- `OrangeHRM_Test_Analysis_Document.md` / `…_Analiz_Dokumani.txt`: Demo
  proje analizi.
- `e2e_analiz_2026-03-30.json`, `test_scenarios_2026-03-30.feature`:
  Belirli bir tarihli manuel analiz çıktıları.

## Politika

1. Bu dizine yeni dosya eklerken, güncel bir değerine çözüm olacaksa
   `docs/` altında resmi bir yere bağlanmalıdır; aksi hâlde burada
   kalmalıdır.
2. Binary dosyalar (`.pptx`, `.pptm`, vb.) `.gitignore` ile kök dışında
   filtrelenir; bu dizin geçiş amaçlıdır ve uzun vadede bulut depolamaya
   taşınmalıdır.
