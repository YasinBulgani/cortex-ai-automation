import urllib.request
import zipfile
import os
import sqlite3
import pandas as pd

# UCI Bank Marketing Dataset (Gerçek Bankacılık Verisi)
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional.zip"
DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = os.path.join(DIR, "bank-additional.zip")
EXTRACT_DIR = os.path.join(DIR, "bank_data_raw")
DB_PATH = os.path.join(os.path.dirname(DIR), "internet_banking_real.db")

def fetch_and_integrate():
    print(f"🌍 İnternetten gerçek bankacılık veri seti indiriliyor: {URL}")
    urllib.request.urlretrieve(URL, ZIP_PATH)
    
    print("📦 ZIP dosyası çıkartılıyor...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_DIR)
        
    csv_path = os.path.join(EXTRACT_DIR, "bank-additional", "bank-additional-full.csv")
    
    print(f"📊 Veri okunuyor: {csv_path}")
    df = pd.read_csv(csv_path, sep=";")
    
    print(f"💾 SQLite veritabanına entegre ediliyor (Toplam: {len(df)} satır)...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Müşteri (Client) Demografik Tablosu
    clients = df[['age', 'job', 'marital', 'education', 'default', 'housing', 'loan']].copy()
    clients.index.name = 'client_id'
    clients.to_sql('real_clients', conn, if_exists='replace')
    
    # 2. Banka İletişim / Pazarlama Tablosu
    campaigns = df[['contact', 'month', 'day_of_week', 'duration', 'campaign', 'pdays', 'previous', 'poutcome']].copy()
    campaigns['client_id'] = clients.index
    campaigns.index.name = 'campaign_id'
    campaigns.to_sql('real_campaigns', conn, if_exists='replace')
    
    # 3. Ekonomik Göstergeler (Makroekonomik veriler)
    economics = df[['emp.var.rate', 'cons.price.idx', 'cons.conf.idx', 'euribor3m', 'nr.employed', 'y']].copy()
    economics['client_id'] = clients.index
    economics.index.name = 'eco_id'
    economics.to_sql('real_economic_indicators', conn, if_exists='replace')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Gerçek Veritabanı başarıyla entegre edildi: {DB_PATH}")
    
    # Temizlik
    os.remove(ZIP_PATH)

if __name__ == "__main__":
    fetch_and_integrate()
