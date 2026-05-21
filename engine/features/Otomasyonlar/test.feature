Feature: Google Arama ve Yasin Suresi Okuma

Scenario: Kullanıcı Yasin Suresi'ni okur
  Given kullanıcı ana sayfadadır
  When kullanıcı "Ara" metnine tıklar
  When kullanıcı arama kutusuna "yasi" yazar
  When kullanıcı Enter tuşuna basar
  When kullanıcı "yasin" metnine tıklar
  When kullanıcı "Ben robot değilim" kutusuna tıklar
  When kullanıcı "0" kutusuna tıklar
  When kullanıcı "2" kutusuna tıklar
  When kullanıcı "4" kutusuna tıklar
  When kullanıcı "5" kutusuna tıklar
  When kullanıcı "3" kutusuna tıklar
  When kullanıcı "6" kutusuna tıklar
  When kullanıcı "7" kutusuna tıklar
  When kullanıcı "8" kutusuna tıklar
  When kullanıcı "Doğrula" butonuna tıklar
  When kullanıcı "0" kutusuna tıklar
  When kullanıcı "1" kutusuna tıklar
  When kullanıcı "6" kutusuna tıklar
  When kullanıcı "Doğrula" butonuna tıklar
  When kullanıcı "Yasin Suresi Türkçe Oku İslam" linkine tıklar
  Then en az 1 adım başarılı olmalıdır