# language: tr

Özellik: Kimlik Doğrulama ve Oturum Yönetimi
  Platform kullanıcıları JWT tabanlı token ile oturum açar,
  korumalı kaynaklara erişir ve oturumlarını yönetir.

  Arka plan:
    Diyelim ki backend API "http://127.0.0.1:8000" adresinde çalışıyor
    Ve admin kullanıcısı "admin@example.com" / "admin123" olarak mevcut

  @critical @pozitif
  Senaryo: Geçerli bilgilerle başarılı oturum açma
    Diyelim ki kullanıcı login endpoint'ine istek hazırlıyor
    Ve e-posta alanına "admin@example.com" yazıyor
    Ve parola alanına "admin123" yazıyor
    O zaman POST "/api/v1/auth/login" isteği gönderilir
    Ve yanıt kodu 200 olmalı
    Ve yanıtta "access_token" alanı dolu olmalı
    Ve yanıtta "token_type" değeri "bearer" olmalı
    Ve token JWT formatında (3 nokta-ayrılmış segment) olmalı

  @critical @negatif
  Senaryo: Hatalı parola ile oturum açma reddedilir
    Diyelim ki kullanıcı login endpoint'ine istek hazırlıyor
    Ve e-posta alanına "admin@example.com" yazıyor
    Ve parola alanına "yanlis_parola" yazıyor
    O zaman POST "/api/v1/auth/login" isteği gönderilir
    Ve yanıt kodu 401 olmalı
    Ve yanıtta "E-posta veya parola hatalı" mesajı olmalı

  @high @negatif
  Senaryo: Kayıtlı olmayan e-posta ile oturum açma reddedilir
    Diyelim ki kullanıcı login endpoint'ine istek hazırlıyor
    Ve e-posta alanına "yok@test.com" yazıyor
    Ve parola alanına "herhangi" yazıyor
    O zaman POST "/api/v1/auth/login" isteği gönderilir
    Ve yanıt kodu 401 olmalı

  @high @negatif
  Senaryo: Devre dışı bırakılmış hesap oturum açamaz
    Diyelim ki "devre_disi@test.com" kullanıcısı devre dışı bırakılmış
    O zaman bu kullanıcının bilgileriyle login isteği gönderilir
    Ve yanıt kodu 403 olmalı
    Ve yanıtta "Hesap devre dışı" mesajı olmalı

  @boundary
  Senaryo Taslağı: Geçersiz giriş verileri ile validation hatası
    Diyelim ki kullanıcı login endpoint'ine istek hazırlıyor
    Ve e-posta alanına "<email>" yazıyor
    Ve parola alanına "<parola>" yazıyor
    O zaman POST "/api/v1/auth/login" isteği gönderilir
    Ve yanıt kodu <kod> olmalı

    Örnekler:
      | email              | parola   | kod |
      |                    | admin123 | 422 |
      | admin@example.com  |          | 422 |
      | gecersiz-format    | admin123 | 422 |

  @high @pozitif
  Senaryo: Geçerli token ile kullanıcı bilgileri alınır
    Diyelim ki admin kullanıcısı oturum açmış ve token almış
    O zaman GET "/api/v1/auth/me" isteği token ile gönderilir
    Ve yanıt kodu 200 olmalı
    Ve yanıtta "id" alanı dolu olmalı
    Ve yanıtta "email" değeri "admin@example.com" olmalı
    Ve yanıtta "roles" listesi boş olmamalı

  @critical @negatif
  Senaryo: Token olmadan korumalı endpoint'e erişim engellenir
    Diyelim ki Authorization header gönderilmiyor
    O zaman GET "/api/v1/tspm/projects" isteği gönderilir
    Ve yanıt kodu 401 veya 403 olmalı

  @medium @pozitif
  Senaryo: Başarılı login sonrası audit log kaydı oluşturulur
    Diyelim ki admin kullanıcısı başarılı login yapmış
    O zaman veritabanında audit_logs tablosu kontrol edilir
    Ve "auth.login" aksiyonlu kayıt bulunmalı
    Ve actor_user_id admin kullanıcısının ID'si olmalı
