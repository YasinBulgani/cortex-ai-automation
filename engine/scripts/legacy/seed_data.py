import sys
from pathlib import Path
import random
import datetime

# Proje kök dizinini yola ekle
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from core.db import get_connection

def seed_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        print("Veritabanı temizleniyor...")
        cursor.execute("DELETE FROM mock_users")
        cursor.execute("DELETE FROM mock_products")
        cursor.execute("DELETE FROM test_runs")
        cursor.execute("DELETE FROM regression_set_features")
        cursor.execute("DELETE FROM regression_sets")
        cursor.execute("DELETE FROM manual_test_steps")
        cursor.execute("DELETE FROM manual_tests")
        cursor.execute("DELETE FROM object_repository")
        cursor.execute("DELETE FROM platform_users")
        
        # 1. Mock Users (15 user)
        print("Mock Users ekleniyor...")
        users = [
            ("admin", "admin@test.com", "admin123", "admin", True),
            ("user1", "user1@test.com", "pass123", "customer", True),
            ("test_ai", "ai@test.com", "ai123", "customer", True),
            ("editor_john", "john.editor@test.com", "ed123", "editor", True),
            ("manager_sara", "sara.manager@test.com", "mgr123", "manager", True),
            ("tester_bob", "bob.tester@test.com", "tst123", "tester", True),
            ("customer_alice", "alice@test.com", "cst123", "customer", True),
            ("customer_mike", "mike@test.com", "cst123", "customer", True),
            ("customer_emma", "emma@test.com", "cst123", "customer", True),
            ("customer_chris", "chris@test.com", "cst123", "customer", False),
            ("customer_lily", "lily@test.com", "cst123", "customer", True),
            ("support_tom", "tom.support@test.com", "sup123", "support", True),
            ("finance_jane", "jane.finance@test.com", "fin123", "finance", True),
            ("admin_backup", "admin.backup@test.com", "admin123", "admin", True),
            ("guest_001", "guest1@test.com", "gst123", "guest", True),
            ("dev_omar", "omar.dev@test.com", "dev123", "developer", True)
        ]
        cursor.executemany(
            "INSERT INTO mock_users (username, email, password, role, is_active) VALUES (?, ?, ?, ?, ?)",
            users
        )

        # 2. Mock Products (20 product)
        print("Mock Products ekleniyor...")
        products = [
            ("Playwright Pro Lisans", 199.99, "Software", 100),
            ("Otomasyon Kitabı", 29.50, "Books", 50),
            ("Mekanik Klavye", 89.00, "Hardware", 15),
            ("Kablosuz Mouse", 45.00, "Hardware", 120),
            ("Geniş Monitör", 300.00, "Hardware", 30),
            ("USB Hub", 15.99, "Accessories", 200),
            ("Laptop Standı", 25.00, "Accessories", 80),
            ("Python Eğitim Seti", 49.99, "Software", 500),
            ("Selenium Elite", 149.99, "Software", 50),
            ("Cypress Masterclass", 99.00, "Software", 75),
            ("Algoritma Kitabı", 35.00, "Books", 110),
            ("SSD 1TB", 120.00, "Hardware", 40),
            ("Harici Disk 2TB", 80.00, "Hardware", 60),
            ("Ergonomik Sandalye", 250.00, "Furniture", 20),
            ("Çalışma Masası", 180.00, "Furniture", 10),
            ("Webcam HD", 60.00, "Hardware", 90),
            ("Gürültü Önleyici Kulaklık", 150.00, "Hardware", 25),
            ("Bluetooth Hoparlör", 40.00, "Hardware", 150),
            ("MousePad XL", 20.00, "Accessories", 300),
            ("HDMI Kablo", 10.00, "Accessories", 400),
            ("Type-C Adaptör", 25.00, "Accessories", 250)
        ]
        cursor.executemany(
            "INSERT INTO mock_products (name, price, category, stock) VALUES (?, ?, ?, ?)",
            products
        )

        # 3. Test Runs (20 runs)
        print("Test Runs ekleniyor...")
        now = datetime.datetime.now()
        run_data = []
        markers_list = ["@smoke", "@regression", "@login", "@search", "@e2e", "@api", "@checkout"]
        for i in range(1, 21):
            run_id = f"RUN-{now.strftime('%Y%m%d')}-{1000 + i}"
            marker = random.choice(markers_list)
            is_passed = random.random() > 0.2  # %80 success rate
            total_tests = random.randint(5, 50)
            if is_passed:
                passed = total_tests
                failed = 0
            else:
                failed = random.randint(1, total_tests // 2)
                passed = total_tests - failed
                
            duration_ms = random.randint(5000, 120000)
            # Zamanları geriye dönük dağıt
            timestamp = now - datetime.timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
            
            run_data.append((run_id, marker, passed, failed, duration_ms, timestamp))
            
        # Zamana göre sırala (eskiden yeniye)
        run_data.sort(key=lambda x: x[5])
        cursor.executemany(
            "INSERT INTO test_runs (run_id, markers, passed, failed, duration_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            run_data
        )

        # 4. Regression Sets (5 sets)
        print("Regression Sets ekleniyor...")
        sets = [
            ("Smoke Test Suite",),
            ("Full Regression",),
            ("Login & Auth Suite",),
            ("E-Commerce Flow",),
            ("API Endpoints",)
        ]
        cursor.executemany("INSERT INTO regression_sets (name) VALUES (?)", sets)
        
        # OLUŞTURULAN SET ID'lerini al
        cursor.execute("SELECT id, name FROM regression_sets")
        set_rows = cursor.fetchall()
        
        feature_mapping = {
            "Smoke Test Suite": ["login.feature", "arama.feature", "home.feature"],
            "Full Regression": ["login.feature", "arama.feature", "home.feature", "checkout.feature", "profile.feature"],
            "Login & Auth Suite": ["login.feature", "register.feature", "reset_password.feature"],
            "E-Commerce Flow": ["arama.feature", "cart.feature", "checkout.feature", "payment.feature"],
            "API Endpoints": ["api_users.feature", "api_products.feature", "api_auth.feature"]
        }
        
        set_features = []
        for row in set_rows:
            set_id = row[0]
            name = row[1]
            features = feature_mapping.get(name, ["test.feature"])
            for f in features:
                set_features.append((set_id, f))
                
        cursor.executemany("INSERT INTO regression_set_features (set_id, feature_name) VALUES (?, ?)", set_features)


        # 5. Manual Tests (8 tests)
        print("Manual Tests ekleniyor...")
        manual_tests = [
            ("Kullanıcı Başarılı Giriş Testi",),
            ("Kullanıcı Kayıt Formu Validasyonu",),
            ("Geçersiz Şifre İle Giriş Denemesi",),
            ("Ürün Arama ve Filtreleme",),
            ("Sepete Ürün Ekleme ve Çıkarma",),
            ("Ödeme Ekranı Kredi Kartı Validasyonu",),
            ("Kullanıcı Profil Güncelleme",),
            ("Çoklu Dil Desteği Değişimi",)
        ]
        cursor.executemany("INSERT INTO manual_tests (title) VALUES (?)", manual_tests)
        
        cursor.execute("SELECT id, title FROM manual_tests")
        mt_rows = cursor.fetchall()
        
        test_steps = {
            "Kullanıcı Başarılı Giriş Testi": [
                ("Giriş sayfasına git", "Giriş formu görüntülenmeli"),
                ("Geçerli email ve şifre gir", "Bilgiler alanlara yazılmalı"),
                ("Giriş yap butonuna tıkla", "Ana sayfaya yönlendirilmeli ve kullanıcı adı sağ üstte görülmeli")
            ],
            "Kullanıcı Kayıt Formu Validasyonu": [
                ("Kayıt sayfasına git", "Kayıt formu açılmalı"),
                ("Boş form ile Onayla'ya bas", "Zorunlu alan uyarıları çıkmalı"),
                ("Geçerli veriler gir ve onayla", "Kayıt başarılı mesajı alınmalı")
            ],
            "Sepete Ürün Ekleme ve Çıkarma": [
                ("Ürün sayfasına git", "Ürün detayları görülmeli"),
                ("Sepete Ekle butonuna tıkla", "Sepet ikonu sayacı artmalı"),
                ("Sepete git", "Eklenen ürün sepette görünmeli"),
                ("Ürünü Kaldır butonuna tıkla", "Sepet boşalmalı")
            ]
            # Diğer testler için generic adımlar ekle
        }
        
        mt_steps_data = []
        for row in mt_rows:
            t_id = row[0]
            title = row[1]
            steps = test_steps.get(title, [
                ("Adım 1: Sayfayı aç", "Sayfa tamamen yüklenmeli"),
                ("Adım 2: Aksiyon gerçekleştir", "Beklenen tepki alınmalı"),
                ("Adım 3: Sonucu kontrol et", "İşlem başarıyla tamamlanmalı")
            ])
            for idx, step in enumerate(steps):
                # t_id, step_order, action, expected
                mt_steps_data.append((t_id, idx+1, step[0], step[1]))
                
        cursor.executemany(
            "INSERT INTO manual_test_steps (test_id, step_order, action, expected) VALUES (?, ?, ?, ?)", 
            mt_steps_data
        )

        # 6. Object Repository (20 locators)
        print("Object Repository ekleniyor...")
        locators = [
            ("LoginUsernameInput", "input[name='username']", "https://example.com/login"),
            ("LoginPasswordInput", "input[name='password']", "https://example.com/login"),
            ("LoginSubmitButton", "button[type='submit']", "https://example.com/login"),
            ("HeaderSearchInput", "#search-box", "Global"),
            ("HeaderSearchButton", ".search-btn", "Global"),
            ("CartIcon", ".cart-icon", "Global"),
            ("LogoutButton", "//button[contains(text(), 'Logout')]", "Global"),
            ("ProductTitle", "h1.product-title", "/product/detail"),
            ("AddToCartBtn", "#add-to-cart", "/product/detail"),
            ("CartItemTitle", ".cart-item h3", "/cart"),
            ("CheckoutBtn", ".checkout-button", "/cart"),
            ("PaymentCardInput", "input[name='card_number']", "/checkout"),
            ("PaymentExpDate", "input[name='exp_date']", "/checkout"),
            ("PaymentCVC", "input[name='cvc']", "/checkout"),
            ("ConfirmOrderBtn", "#confirm-order", "/checkout"),
            ("OrderSuccessMsg", ".success-message", "/order/success"),
            ("ProfileNameInput", "input[name='first_name']", "/profile"),
            ("ProfileSaveBtn", "button.save-profile", "/profile"),
            ("LanguageDropdown", "#lang-selector", "Global"),
            ("FooterContactLink", "a[href='/contact']", "Global")
        ]
        cursor.executemany("INSERT INTO object_repository (name, locator_value, page_url) VALUES (?, ?, ?)", locators)

        # 7. Platform Users (2 users)
        print("Platform Users ekleniyor...")
        p_users = [
            ("admin@platform.com", "scrypt:32768:8:1$DMMKjO0Lz2Bq1LDE$251b68ceeba9f7ab01e8ce4a7dff60a0b2fd8cc0cd97e55ce9efb5006b5dffec045feefaf20fde71a80bebed7669d0d1b32d2c12513ee63ee6a0328a9b2b5126", 1, None),
            ("tester@platform.com", "scrypt:32768:8:1$UuT6g6tI$0c1f26fdb8533b3a726abda50ad5c0b62b08fa5ef60d5b62b781a967c13ac47e1fa1e976077ab9ccbfdb841fdaf97e29fbe9f790c102b37bd32a249c5952d716", 1, None)
        ]
        # NOTE: Şifreler rastgele üretilmiş scrypt hashleridir, production olarak kullanılmamalı.
        # Bunlar test giriş yapabilmek için sembolik. Aslında uygulamanın kendi hashlemesiyle yapılmalı ama 
        # şimdilik app çalıştığında kayıt olarak girerlerse de olur. Biz yinede ekleyelim.
        cursor.executemany("INSERT INTO platform_users (email, password_hash, is_verified, verification_token) VALUES (?, ?, ?, ?)", p_users)

        conn.commit()
        print("Veritabanı başarıyla dolduruldu!")

if __name__ == "__main__":
    seed_database()
