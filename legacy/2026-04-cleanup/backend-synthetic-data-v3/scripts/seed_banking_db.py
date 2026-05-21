"""
Büyük çaplı bankacılık veritabanı oluşturucu.
Bu script:
1. Müşteri, Hesap, İşlem (Kredi Kartı, Kredi vb. genişletilebilir) tabloları tasarlar.
2. On binlerce satır veri üretir.
3. Bunları `banking_core.db` adlı bir SQLite dosyasına kaydeder.
4. Platforma 'Hazır Bankacılık Projesi' olarak şemaları kaydeder.
"""
import asyncio
import os
import sqlite3
import pandas as pd
from uuid import uuid4

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session
from app.models.schema_model import Project, DetectedSchema, GenerationRule
from app.core.generator import SyntheticGenerator
from app.core.classifier import ColumnClassifier
from app.core.rule_engine import RuleEngine
from app.core.analyzer import SchemaAnalyzer

async def main():
    print("🏦 Dev Bankacılık Veritabanı entegrasyonu başlıyor...")
    
    # Şema Tanımları
    musteri_cols = [
        {"name": "musteri_id", "dtype": "int", "classification": "id"},
        {"name": "tc_kimlik", "dtype": "string", "classification": "tc_kimlik", "pii": True},
        {"name": "ad_soyad", "dtype": "string", "classification": "name", "pii": True},
        {"name": "dogum_tarihi", "dtype": "string", "classification": "datetime"},
        {"name": "telefon", "dtype": "string", "classification": "phone", "pii": True},
        {"name": "email", "dtype": "string", "classification": "email", "pii": True},
        {"name": "meslek", "dtype": "string", "classification": "unknown"},
        {"name": "aylik_gelir", "dtype": "float", "classification": "unknown", "stats": {"min": 17002, "max": 250000, "mean": 45000, "std": 30000}},
        {"name": "risk_skoru", "dtype": "int", "classification": "unknown", "stats": {"min": 1, "max": 5, "mean": 3, "std": 1}},
        {"name": "musteri_segmenti", "dtype": "string", "classification": "enum", "stats": {"top_values": {"Bireysel": 0.6, "Premium": 0.3, "Kurumsal": 0.1}}},
        {"name": "kayit_tarihi", "dtype": "string", "classification": "datetime", "stats": {"min_date": "2015-01-01", "max_date": "2024-01-01"}}
    ]

    hesap_cols = [
        {"name": "hesap_id", "dtype": "int", "classification": "id"},
        {"name": "musteri_id", "dtype": "int", "classification": "foreign_key"},
        {"name": "iban", "dtype": "string", "classification": "iban", "pii": True},
        {"name": "hesap_turu", "dtype": "string", "classification": "enum", "stats": {"top_values": {"Vadesiz TL": 0.5, "Vadeli TL": 0.2, "Vadesiz USD": 0.15, "Vadesiz EUR": 0.1, "Altın": 0.05}}},
        {"name": "bakiye", "dtype": "float", "classification": "unknown", "stats": {"min": 0, "max": 1500000, "mean": 75000, "std": 150000}},
        {"name": "acilis_tarihi", "dtype": "string", "classification": "datetime", "stats": {"min_date": "2015-01-01", "max_date": "2024-01-01"}},
        {"name": "durum", "dtype": "string", "classification": "enum", "stats": {"top_values": {"Aktif": 0.9, "Blokeli": 0.05, "Kapalı": 0.05}}}
    ]

    islem_cols = [
        {"name": "islem_id", "dtype": "int", "classification": "id"},
        {"name": "gonderen_hesap_id", "dtype": "int", "classification": "foreign_key"},
        {"name": "alici_iban", "dtype": "string", "classification": "iban", "pii": True},
        {"name": "islem_turu", "dtype": "string", "classification": "enum", "stats": {"top_values": {"EFT": 0.4, "Havale": 0.3, "Fatura Ödeme": 0.15, "Kredi Kartı Ödeme": 0.1, "Kurum Ödemesi": 0.05}}},
        {"name": "tutar", "dtype": "float", "classification": "unknown", "stats": {"min": 10, "max": 500000, "mean": 4500, "std": 15000}},
        {"name": "islem_tarihi", "dtype": "string", "classification": "datetime", "stats": {"min_date": "2024-01-01", "max_date": "2024-12-31"}},
        {"name": "aciklama", "dtype": "string", "classification": "unknown", "stats": {"min_length": 5, "max_length": 50}},
        {"name": "islem_kanali", "dtype": "string", "classification": "enum", "stats": {"top_values": {"Mobil": 0.7, "Internet": 0.15, "ATM": 0.1, "Sube": 0.05}}}
    ]

    kredi_karti_cols = [
        {"name": "kart_id", "dtype": "int", "classification": "id"},
        {"name": "musteri_id", "dtype": "int", "classification": "foreign_key"},
        {"name": "kart_numarasi", "dtype": "string", "classification": "credit_card", "pii": True},
        {"name": "limit", "dtype": "float", "classification": "unknown", "stats": {"min": 10000, "max": 500000, "mean": 75000, "std": 50000}},
        {"name": "kullanilabilir_limit", "dtype": "float", "classification": "unknown", "stats": {"min": 0, "max": 500000, "mean": 25000, "std": 30000}},
        {"name": "asgari_odeme", "dtype": "float", "classification": "unknown", "stats": {"min": 0, "max": 50000, "mean": 5000, "std": 8000}},
        {"name": "son_kullanma_tarihi", "dtype": "string", "classification": "datetime", "stats": {"min_date": "2025-01-01", "max_date": "2032-12-31"}}
    ]

    schemas = [
        {"table_name": "musteriler", "columns": musteri_cols},
        {"table_name": "hesaplar", "columns": hesap_cols},
        {"table_name": "islemler", "columns": islem_cols},
        {"table_name": "kredi_kartlari", "columns": kredi_karti_cols}
    ]

    relationships = [
        {"from_table": "hesaplar", "from_column": "musteri_id", "to_table": "musteriler", "to_column": "musteri_id"},
        {"from_table": "islemler", "from_column": "gonderen_hesap_id", "to_table": "hesaplar", "to_column": "hesap_id"},
        {"from_table": "kredi_kartlari", "from_column": "musteri_id", "to_table": "musteriler", "to_column": "musteri_id"}
    ]

    engine = RuleEngine()
    gen = SyntheticGenerator()

    # Kural çıkarımı
    rules_map = {}
    for scl in schemas:
        rules = engine.infer_rules(scl)
        # Bazı kolonlar için manuel düzeltme (isim, meslek vs.)
        for r in rules:
            if r["column_name"] == "meslek":
                r["rule_type"] = "faker"
                r["rule_config"] = {"provider": "job", "locale": "tr_TR"}
            elif r["column_name"] == "aciklama":
                r["rule_type"] = "faker"
                r["rule_config"] = {"provider": "sentence", "locale": "tr_TR"}
            elif r["column_name"] == "dogum_tarihi":
                r["rule_type"] = "date_range"
                r["rule_config"] = {"start_date": "1950-01-01", "end_date": "2005-12-31"}
        rules_map[scl["table_name"]] = rules

    print("🧩 Veriler Üretiliyor (Bu işlem birkaç saniye sürebilir)...")
    # Gerçek boyutlar: 10,000 Müşteri, 20,000 Hesap, 100,000 İşlem, 15,000 Kart
    row_counts = {
        "musteriler": 10000,
        "hesaplar": 20000,
        "islemler": 100000,
        "kredi_kartlari": 15000
    }

    generated_dfs = gen.generate_multi_table(schemas, rules_map, relationships, row_counts)

    print("💾 SQLite 'banking_core.db' dosyasına yazılıyor...")
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'banking_core.db')
    conn = sqlite3.connect(db_path)
    
    for table_name, df in generated_dfs.items():
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"   ✓ {table_name} ({len(df):,} satır)")
    
    conn.close()

    print("🌐 Sentetik Veri Platformu Dashboard'una 'Örnek Proje' olarak ekleniyor...")
    async with async_session() as session:
        project = Project(
            name="🏦 Merkez Bankacılık Core DB",
            description="10.000 Müşteri, 20.000 Hesap, 100.000 İşlem ve 15.000 Kredi Kartı içeren tam donanımlı bankacılık veritabanı şeması."
        )
        session.add(project)
        await session.flush()

        for scl in schemas:
            t_name = scl["table_name"]
            db_schema = DetectedSchema(
                project_id=project.id,
                table_name=t_name,
                source_type="database",
                source_info="banking_core.db",
                row_count=row_counts[t_name],
                columns=scl["columns"],
                relationships=[rel for rel in relationships if rel["from_table"] == t_name]
            )
            session.add(db_schema)
            await session.flush()

            for rule in rules_map[t_name]:
                db_rule = GenerationRule(
                    schema_id=db_schema.id,
                    column_name=rule["column_name"],
                    rule_type=rule["rule_type"],
                    rule_config=rule.get("rule_config", {}),
                )
                session.add(db_rule)
        
        await session.commit()
    
    print("✅ Başarıyla tamamlandı! banking_core.db hazır ve arayüze eklendi.")

if __name__ == "__main__":
    asyncio.run(main())
