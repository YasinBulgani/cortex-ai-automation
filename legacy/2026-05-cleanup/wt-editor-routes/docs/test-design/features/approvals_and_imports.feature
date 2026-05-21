# language: tr

Özellik: Onay Kuyruğu ve İçe Aktarma
  AI taslakları onay kuyruğundan geçirilir.
  Dış kaynaklardan dosya içe aktarılır.

  Arka plan:
    Diyelim ki kullanıcı oturum açmış
    Ve projede senaryolar mevcut

  # ═══════════════════════════════════════════════════════════
  # Onay Kuyruğu
  # ═══════════════════════════════════════════════════════════

  @critical @pozitif
  Senaryo: Onay kabul etme
    Diyelim ki projede "pending" statusünde bir onay mevcut
    O zaman onay için "approved" kararı gönderilir
    Ve yanıt başarılı olmalı
    Ve onay statusü "approved" olmalı
    Ve "decided_at" zaman damgası dolu olmalı

  @high @pozitif
  Senaryo: Onay reddetme
    Diyelim ki projede "pending" statusünde bir onay mevcut
    O zaman onay için "rejected" kararı gönderilir
    Ve yanıt başarılı olmalı
    Ve onay statusü "rejected" olmalı

  @medium @negatif
  Senaryo: Var olmayan onay için karar
    O zaman var olmayan onay ID'si ile karar gönderilir
    Ve yanıt kodu 404 olmalı
    Ve yanıtta "Onay bulunamadı" mesajı olmalı

  @high @pozitif
  Senaryo: Onay listesi görüntüleme
    Diyelim ki projede 3 onay mevcut (1 pending, 1 approved, 1 rejected)
    O zaman onay listesi istenir
    Ve yanıtta 3 onay dönmeli
    Ve her onayda "id", "title", "status" alanları olmalı

  # ═══════════════════════════════════════════════════════════
  # İçe Aktarma
  # ═══════════════════════════════════════════════════════════

  @high @pozitif
  Senaryo: Import kaydı oluşturma
    Diyelim ki import verisi hazırlanıyor
    Ve dosya adı "analiz_dokumani.pdf" olarak belirleniyor
    Ve ham metin "Kullanıcı giriş yapabilmeli..." olarak sağlanıyor
    O zaman POST ".../imports" isteği gönderilir
    Ve yanıt kodu 201 olmalı
    Ve yanıtta "status" değeri "completed" olmalı

  @medium @boundary
  Senaryo: Boş dosya adıyla import
    Diyelim ki dosya adı boş bırakılıyor
    O zaman POST ".../imports" isteği gönderilir
    Ve yanıt kodu 422 olmalı
