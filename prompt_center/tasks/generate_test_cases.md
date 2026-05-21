Görev:
Verilen modül, özellik, gereksinim veya analist dokümanından kapsamlı manuel test case listesi üret. Çıktı yapılandırılmış JSON olmalı.

# Kalite kuralları

- **Test ID** formatı: `TC-XXX` benzersiz ve sıralı.
- **Başlıklar** kısa ama ayırt edici olsun; modül + davranışı yansıtsın.
- **Preconditions** gerçekten gerekli olan ön koşullarla sınırlı olsun; gereksiz adım ekleme.
- **Steps** atomik ve uygulanabilir; bir test uzmanı sırasıyla uygulayabilmeli.
- **Expected result** ölçülebilir/gözlemlenebilir olsun. "Başarılı olur" yerine "Dashboard sayfasına yönlendirilir ve kullanıcı menüsünde 'Hoş geldiniz, X' yazısı görünür" gibi somut yaz.
- Aynı senaryoyu farklı veriyle tekrar etmek yerine kapsamı genişleten yeni vaka ekle.
- Doküman eksikse `notes` alanında açıkça belirt; eksik bilgiden senaryo uydurma.

# Zorunlu kategori dağılımı

Her özellik/modül için **EN AZ 3-5 senaryo** üret ve aşağıdaki 5 kategoriyi mutlaka kapsa:

| Kategori | Açıklama |
|----------|----------|
| `positive` | Happy path — normal akış, geçerli veri |
| `negative` | Hata durumları, geçersiz veri, validasyon mesajları |
| `boundary` | Min/max değerler, boş/null, çok uzun string, karakter limitleri |
| `security` | Yetkilendirme, RBAC, SQL injection, XSS, session hijack, KVKK ihlali, log/audit |
| `integration` | Modüller arası etkileşim, dış servis (API, DB, queue, e-posta) entegrasyonları, race condition |

`edge_case` ek kategori olarak kullanılabilir ama yukarıdaki 5'ten birinin yerine geçemez.

# Çıktı şeması

```json
{
  "test_cases": [
    {
      "id": "TC-001",
      "title": "Geçerli kullanıcı başarıyla giriş yapar",
      "description": "Doğru email + şifre kombinasyonuyla dashboard'a yönlendirme",
      "module": "Kimlik Doğrulama",
      "preconditions": ["Kullanıcı kayıtlı ve aktif", "Test ortamında DB temiz"],
      "steps": [
        "Login sayfasını aç",
        "Email alanına geçerli adres gir",
        "Şifre alanına doğru şifreyi gir",
        "Giriş Yap butonuna tıkla"
      ],
      "test_data": {"email": "test@example.com", "password": "Valid123!"},
      "expected_result": "Kullanıcı /dashboard sayfasına yönlendirilir, sağ üstte 'Hoş geldiniz, Test' yazısı görünür, audit log'a login event'i düşer",
      "test_type": "positive",
      "priority": "high",
      "tags": ["login", "smoke", "auth"],
      "automatable": true,
      "notes": ""
    },
    {
      "id": "TC-002",
      "title": "Yanlış şifre 5 kez denendiğinde hesap kilitlenir",
      "module": "Kimlik Doğrulama",
      "preconditions": ["Kullanıcı kayıtlı"],
      "steps": [
        "Login sayfasını aç",
        "Geçerli email + yanlış şifre kombinasyonu ile 5 kez giriş dene",
        "6. denemeyi yap"
      ],
      "test_data": {"email": "test@example.com", "wrong_password": "WrongPass!"},
      "expected_result": "5. denemeden sonra 'Hesabınız 15 dakika kilitlendi' mesajı görünür, 6. deneme aynı mesajı verir, audit log'a 'account_locked' event'i düşer",
      "test_type": "security",
      "priority": "high",
      "tags": ["login", "security", "brute-force"],
      "automatable": true,
      "notes": "BDDK gereği başarısız deneme limiti loglanmalı"
    }
  ],
  "summary": {
    "total": 2,
    "by_type": {"positive": 1, "negative": 0, "boundary": 0, "security": 1, "integration": 0},
    "by_priority": {"high": 2, "medium": 0, "low": 0},
    "coverage_notes": "Sadece login akışı işlendi. Şifre sıfırlama, oturum süresi ve oturum kapatma ayrı analiz turunda işlenmeli."
  }
}
```

# Few-shot örnek (kısa)

Girdi:
> "Kullanıcı sisteme email ve şifreyle giriş yapar. Şifre yanlışsa 'Hatalı şifre' uyarısı çıkar. 3 başarısız denemede hesap 15 dk kilitlenir. Şifre minimum 8 karakter, en az 1 büyük harf + 1 rakam içermeli."

Beklenen çıktı (özet):
- TC-001 positive: Geçerli giriş
- TC-002 negative: Yanlış şifre → uyarı
- TC-003 boundary: 7 karakter şifre → reddedilir
- TC-004 boundary: 8 karakter ama büyük harf yok → reddedilir
- TC-005 security: 3 hatalı deneme → kilit + audit log

Yanıt yalnızca yukarıdaki JSON şemasına uyan geçerli JSON içeriği olmalı. Açıklayıcı metin, kod bloğu işareti veya markdown yorum ekleme.
