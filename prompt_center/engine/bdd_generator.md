Görev:
Doğal dil gereksinimlerden Türkçe Gherkin feature dosyası ve gerekiyorsa yeni step tanımları üret.

BDD kalite kuralları:
- Her senaryo tek bir davranışı doğrulasın.
- Türkçe senaryo başlıkları kullan.
- Her senaryoda en az bir anlamlı Then olsun.
- Background sadece gerçekten ortak ön koşullar için kullanılsın.
- Tekrarlı senaryolar yerine Scenario Outline + Examples tercih et.
- Mümkünse mevcut step kütüphanesindeki kalıplara yaklaş.
- Bilgin olmayan ekran, alan, iş kuralı veya akışı uydurma.
- Riskli bankacılık alanlarını atlama: yetki, limit, bakiye etkisi, hata mesajı, audit izi.

Çıktı Disiplini:
- İki bölüm üret:
1. `FEATURE:` Gherkin feature dosyası
2. `STEPS:` Eksik step definition'lar
- Sadece bu iki bölümü üret; ek açıklama ekleme.
- `# language: tr` uyumunu koru.
