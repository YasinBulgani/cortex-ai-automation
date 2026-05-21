import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database.sqlite"

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Seed Test Runs (for Dashboard)
    print("Seeding test_runs...")
    markers = ["smoke", "not ai", "P1", "P2", "regression"]
    for i in range(20):
        run_id = f"RUN_{20260300 + i}"
        marker = random.choice(markers)
        passed = random.randint(5, 15)
        failed = random.randint(0, 3)
        duration = random.randint(10000, 50000)
        # Random timestamp in the last 7 days
        ts = datetime.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))
        
        cursor.execute("""
            INSERT OR IGNORE INTO test_runs (run_id, markers, passed, failed, duration_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, marker, passed, failed, duration, ts))

    # 2. Seed Locators (for Element Depot)
    print("Seeding object_repository...")
    locators = [
        ("login_username", "//input[@id='user-name']", "https://www.saucedemo.com/"),
        ("login_password", "//input[@id='password']", "https://www.saucedemo.com/"),
        ("login_button", "//input[@id='login-button']", "https://www.saucedemo.com/"),
        ("add_to_cart_btn", "//button[contains(@text, 'Add to cart')]", "https://www.saucedemo.com/inventory.html"),
        ("shopping_cart", ".shopping_cart_link", "https://www.saucedemo.com/inventory.html"),
        ("checkout_btn", "#checkout", "https://www.saucedemo.com/cart.html"),
        ("first_name", "[data-test='firstName']", "https://www.saucedemo.com/checkout-step-one.html"),
        ("last_name", "[data-test='lastName']", "https://www.saucedemo.com/checkout-step-one.html"),
        ("postal_code", "[data-test='postalCode']", "https://www.saucedemo.com/checkout-step-one.html"),
        ("continue_btn", "#continue", "https://www.saucedemo.com/checkout-step-one.html"),
        ("finish_btn", "#finish", "https://www.saucedemo.com/checkout-step-two.html"),
    ]
    for name, val, url in locators:
        cursor.execute("""
            INSERT OR IGNORE INTO object_repository (name, locator_value, page_url)
            VALUES (?, ?, ?)
        """, (name, val, url))

    # 3. Seed Manual Tests
    print("Seeding manual_tests...")
    manual_tests = [
        ("Login Fonksiyonu Pozitif Test", "Passed"),
        ("Yanlış Şifre ile Giriş Denemesi", "Passed"),
        ("Sepete Ürün Ekleme/Çıkarma", "In Progress"),
        ("Ödeme Sayfası Form Doğrulama", "Unexecuted"),
    ]
    for title, status in manual_tests:
        cursor.execute("INSERT INTO manual_tests (title, status) VALUES (?, ?)", (title, status))
        test_id = cursor.lastrowid
        
        steps = [
            ("Kullanıcı adını gir", "Giriş başarılı olmalı"),
            ("Şifreyi gir", "Yıldızlı görünmeli"),
            ("Login butonuna bas", "Dashboard açılmalı"),
        ]
        for i, (action, expected) in enumerate(steps):
            cursor.execute("""
                INSERT INTO manual_test_steps (test_id, step_order, action, expected, status)
                VALUES (?, ?, ?, ?, ?)
            """, (test_id, i+1, action, expected, "Passed" if status == "Passed" else "Unexecuted"))

    conn.commit()
    conn.close()
    print("Success: Database seeded with dummy data.")

if __name__ == "__main__":
    seed()
