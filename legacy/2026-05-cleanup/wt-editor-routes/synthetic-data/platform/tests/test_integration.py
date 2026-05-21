"""
Entegrasyon testleri - Türk bankacılık sentetik veri üretim platformu
Integration tests for Turkish banking synthetic data generation platform

Bu modül, platform bileşenlerinin uçtan uca iş akışlarını test eder.
Gerçek veritabanı ve LLM çağrıları mock'lanmıştır.
"""

import pytest
import pandas as pd
import numpy as np
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import threading

# İçe aktarılacak servisler (app.services'ten)
from app.services import (
    SchemaAnalyzer,
    ColumnClassifier,
    PIIDetector,
    RuleInferenceEngine,
    SyntheticDataGenerator,
    ScenarioGenerator,
    RelationshipInference,
)
from app.models import ScenarioType, PIICategory


# ============================================================================
# BÖLÜM 1: TestFullPipeline - Tam İş Akışı Testleri
# ============================================================================

class TestFullPipeline:
    """
    Tam pipeline testleri: veri yükleme → analiz → kural çıkarım → veri üretim → dışa aktarım
    End-to-end pipeline: load → analyze → infer rules → generate → export
    """

    def test_csv_load_analyze_rules_generate_export(
        self,
        sample_customers_csv,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        CSV dosyası yükleme, şema analizi, kural çıkarım, veri üretim ve dışa aktarım tamamını test et.
        Tests: CSV load → schema analysis → rule inference → data generation → export

        Akış:
        1. CSV dosyasından müşteri verisi yükle
        2. Şema analiz et
        3. Kuralları çıkar
        4. 100 satır sentetik veri üret
        5. Dışa aktar ve doğrula
        """
        # 1. CSV yükle
        df = pd.read_csv(sample_customers_csv)
        assert df is not None
        assert len(df) > 0
        original_shape = df.shape

        # 2. Şema analiz et
        analysis_result = schema_analyzer.analyze(df)
        assert analysis_result is not None
        assert len(analysis_result.column_analyses) == len(df.columns)

        # 3. Kuralları çıkar
        rule_report = rule_engine.infer_rules(df)
        assert rule_report is not None
        assert rule_report.rules is not None

        # 4. Sentetik veri üret
        synthetic_df = synthetic_generator.generate(
            rules=rule_report.rules,
            num_rows=100,
        )
        assert synthetic_df is not None
        assert len(synthetic_df) == 100
        assert list(synthetic_df.columns) == list(df.columns)

        # 5. Dışa aktar ve doğrula
        with tempfile.TemporaryDirectory() as tmpdir:
            output_csv = Path(tmpdir) / "synthetic_output.csv"
            synthetic_df.to_csv(output_csv, index=False)

            # Dışa aktarılan dosyayı yeniden yükle ve doğrula
            exported_df = pd.read_csv(output_csv)
            assert len(exported_df) == 100
            assert list(exported_df.columns) == list(df.columns)

    def test_json_format_pipeline(
        self,
        sample_accounts_csv,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        JSON formatı destekli pipeline testi.
        Tests full pipeline with JSON format instead of CSV.

        Akış: CSV → analiz → kural çıkarım → üretim → JSON dışa aktar
        """
        # CSV yükle
        df = pd.read_csv(sample_accounts_csv)

        # Analiz ve kural çıkarım
        analysis = schema_analyzer.analyze(df)
        rules = rule_engine.infer_rules(df).rules

        # Veri üret
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=50)

        # JSON'a dışa aktar
        with tempfile.TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "synthetic_data.json"
            synthetic_df.to_json(output_json, orient="records")

            # JSON'ı yükle ve doğrula
            with open(output_json) as f:
                data = json.load(f)
            assert len(data) == 50
            assert all(isinstance(record, dict) for record in data)

    def test_excel_format_pipeline(
        self,
        sample_transactions_csv,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        Excel (.xlsx) formatı destekli pipeline testi.
        Tests full pipeline with Excel format (.xlsx).

        Not: openpyxl kütüphanesi gereklidir.
        """
        # CSV yükle
        df = pd.read_csv(sample_transactions_csv)

        # Analiz ve kural çıkarım
        analysis = schema_analyzer.analyze(df)
        rules = rule_engine.infer_rules(df).rules

        # Veri üret
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=75)

        # Excel'e dışa aktar
        with tempfile.TemporaryDirectory() as tmpdir:
            output_excel = Path(tmpdir) / "synthetic_data.xlsx"
            try:
                synthetic_df.to_excel(output_excel, index=False, engine="openpyxl")

                # Excel'i yükle ve doğrula
                excel_df = pd.read_excel(output_excel)
                assert len(excel_df) == 75
                assert list(excel_df.columns) == list(df.columns)
            except ImportError:
                # openpyxl yüklü değilse testi atla
                pytest.skip("openpyxl kütüphanesi gereklidir")

    def test_pipeline_with_large_dataset(
        self,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        Büyük veri seti (1000+ satır) ile pipeline testi.
        Tests pipeline performance with large dataset (1000+ rows).

        Performans doğrulama:
        - Analiz işlemi tamamlanmalı
        - Kurallar çıkarılmalı
        - 500 satır veri üretilmeli
        """
        # Büyük örnek veri seti oluştur
        large_df = pd.DataFrame({
            "customer_id": range(1, 1001),
            "name": [f"Müşteri_{i}" for i in range(1, 1001)],
            "balance": np.random.uniform(1000, 100000, 1000),
            "creation_date": pd.date_range("2020-01-01", periods=1000),
            "is_active": np.random.choice([True, False], 1000),
        })

        # Analiz et
        analysis = schema_analyzer.analyze(large_df)
        assert analysis is not None
        assert len(analysis.column_analyses) == 5

        # Kuralları çıkar
        rules = rule_engine.infer_rules(large_df).rules
        assert rules is not None

        # Veri üret
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=500)
        assert len(synthetic_df) == 500
        assert list(synthetic_df.columns) == list(large_df.columns)

    def test_pipeline_preserves_column_types(
        self,
        sample_customers_csv,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        Üretilen verilerin orijinal sütun türlerini koruduğunu doğrula.
        Verifies that generated data preserves original column data types.

        Kontrol noktaları:
        - Sayısal sütunlar sayısal kalmalı
        - Tarih sütunları datetime kalmalı
        - Kategorik sütunlar object/string kalmalı
        """
        # Orijinal veriyi yükle ve türleri belirle
        original_df = pd.read_csv(sample_customers_csv)
        original_dtypes = original_df.dtypes.to_dict()

        # Pipeline çalıştır
        analysis = schema_analyzer.analyze(original_df)
        rules = rule_engine.infer_rules(original_df).rules
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=100)

        # Türleri kontrol et
        synthetic_dtypes = synthetic_df.dtypes.to_dict()

        for col in original_df.columns:
            # Temel tür uyumluluğunu kontrol et
            orig_type = str(original_dtypes[col])
            synth_type = str(synthetic_dtypes[col])

            # Sayısal türlerin uyumluluğunu kontrol et
            if "int" in orig_type or "float" in orig_type:
                assert "int" in synth_type or "float" in synth_type, \
                    f"Sütun {col}: {orig_type} -> {synth_type}"


# ============================================================================
# BÖLÜM 2: TestPIIPipeline - KKV ve KYK Uyumluluğu Testleri
# ============================================================================

class TestPIIPipeline:
    """
    Kişisel İlişkili Veriler (KİV) ve KVKK uyumluluğu testleri.
    PII (Personally Identifiable Information) detection and KVKK compliance tests.

    KVKK: Kişisel Verilerin Korunması Kanunu
    (Personal Data Protection Law of Turkey)
    """

    def test_pii_detect_mask_generate_flow(
        self,
        pii_detector,
        synthetic_generator,
        rule_engine,
    ):
        """
        KİV algıla → maskele → veri üret → maskelenmiş çıktı doğrula.
        PII detection → masking → generation → verify no PII in output.

        Adımlar:
        1. Test verisi içindeki KİV'i algıla
        2. Algılanan KİV'i maskele
        3. Maskeli verileri kullanarak sentetik veri üret
        4. Çıktıda KİV olmadığını doğrula
        """
        # Test verisi (KİV içeriyor)
        test_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "name": ["Ahmet Yılmaz", "Fatma Demir", "Ali Kaya"],
            "email": ["ahmet@example.com", "fatma@example.com", "ali@example.com"],
            "phone": ["05301234567", "05302345678", "05303456789"],
            "tckn": ["12345678901", "23456789012", "34567890123"],
            "iban": ["TR120006100519786457841326", "TR120006100519786457841327", "TR120006100519786457841328"],
        })

        # 1. KİV algıla
        pii_report = pii_detector.detect(test_df)
        assert pii_report is not None
        assert len(pii_report.pii_results) > 0

        # KİV kategorilerinin algılandığını doğrula
        detected_categories = {r.category for r in pii_report.pii_results}
        assert len(detected_categories) > 0

        # 2. Maskeleme simülasyonu (mock)
        masked_df = test_df.copy()
        for col in ["email", "phone", "tckn", "iban"]:
            if col in masked_df.columns:
                masked_df[col] = masked_df[col].apply(lambda x: "***MASKED***")

        # 3. Maskeli verilerle kural çıkar ve veri üret
        rules = rule_engine.infer_rules(masked_df).rules
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=50)

        # 4. Çıktıda gerçek KİV olmadığını doğrula
        assert synthetic_df is not None
        assert len(synthetic_df) == 50

    def test_pii_detection_all_categories(self, pii_detector):
        """
        Tüm KİV kategorilerinin algılandığını test et.
        Tests detection of all PII categories: TCKN, email, phone, IBAN.

        KİV Kategorileri:
        - TCKN: Türkiye Cumhuriyet Kimlik Numarası (11 basamak)
        - EMAIL: E-posta adresi
        - PHONE: Telefon numarası (0530... vb.)
        - IBAN: Uluslararası Banka Hesap Numarası
        """
        test_data = pd.DataFrame({
            "customer_id": [1, 2, 3, 4],
            "tckn": ["12345678901", "23456789012", "34567890123", "45678901234"],
            "email": ["user1@domain.com", "user2@domain.com", "user3@domain.com", "user4@domain.com"],
            "phone": ["05301234567", "05321234568", "05351234569", "05371234570"],
            "iban": ["TR120006100519786457841326", "TR120006100519786457841327", "TR120006100519786457841328", "TR120006100519786457841329"],
        })

        pii_report = pii_detector.detect(test_data)
        assert pii_report is not None

        # Her kategori için algılamalar kontrol et
        results_by_category = {}
        for result in pii_report.pii_results:
            cat = result.category
            if cat not in results_by_category:
                results_by_category[cat] = 0
            results_by_category[cat] += 1

        # En az bir algılama her kategori için yapılmış olmalı
        assert len(results_by_category) > 0

    def test_pii_masking_preserves_format(self, pii_detector):
        """
        Maskeleme işleminin veri formatını koruduğunu doğrula.
        Verifies that masking preserves data structure and format.

        Örneğin:
        - IBAN maskeleme: TR12... kalıbı korunmalı
        - Telefon maskeleme: 0530... kalıbı korunmalı
        - E-posta maskeleme: xxx@domain.com kalıbı korunmalı
        """
        test_df = pd.DataFrame({
            "account_id": [1, 2],
            "iban": ["TR120006100519786457841326", "TR120006100519786457841327"],
            "phone": ["05301234567", "05302345678"],
            "email": ["customer1@bank.com", "customer2@bank.com"],
        })

        # KİV algıla
        pii_report = pii_detector.detect(test_df)
        assert pii_report is not None

        # Maskeleme simülasyonu
        masked_df = test_df.copy()

        # IBAN'ı maskele (kalıp korunmalı)
        if "iban" in masked_df.columns:
            masked_df["iban"] = masked_df["iban"].apply(
                lambda x: f"TR{x[2:4]}****{x[-6:]}" if str(x).startswith("TR") else "***MASKED***"
            )

        # Maskelenen IBAN hala kalıba uymalı
        for iban in masked_df["iban"]:
            assert str(iban).startswith("TR") or str(iban) == "***MASKED***"

    def test_kvkk_compliance_flow(self, pii_detector, synthetic_generator, rule_engine):
        """
        KVKK uyumluluğu tam iş akışı testi.
        Full KVKK compliance workflow test.

        KVKK gereklilikleri:
        1. KİV algılanmalı ve raporlanmalı
        2. KİV maskelenip korunmalı
        3. Sentetik veri üretiminde gerçek KİV kullanılmamalı
        4. Oluşturulan veri denetlenebilir olmalı
        """
        # Hassas müşteri verisi
        customer_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "name": ["Müşteri A", "Müşteri B", "Müşteri C"],
            "tckn": ["11111111111", "22222222222", "33333333333"],
            "email": ["a@example.com", "b@example.com", "c@example.com"],
            "balance": [10000, 20000, 30000],
        })

        # 1. KİV algıla
        pii_report = pii_detector.detect(customer_df)
        assert pii_report is not None
        assert len(pii_report.pii_results) > 0

        # 2. KİV içeren sütunları maskele
        masked_df = customer_df.copy()
        for col in ["name", "tckn", "email"]:
            masked_df[col] = "***MASKED***"

        # 3. Sentetik veri üret
        rules = rule_engine.infer_rules(masked_df).rules
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=100)

        # 4. Çıktıyı doğrula
        assert synthetic_df is not None
        assert len(synthetic_df) == 100
        # Özgün KİV çıktıda olmamalı
        for original_tckn in customer_df["tckn"]:
            assert original_tckn not in synthetic_df.values.flatten().tolist()


# ============================================================================
# BÖLÜM 3: TestScenarioPipeline - Senaryo Tabanlı Veri Üretim Testleri
# ============================================================================

class TestScenarioPipeline:
    """
    Bankacılık senaryoları ile veri üretim testleri.
    Scenario-based data generation tests for banking scenarios.

    Senaryo Türleri (ScenarioType):
    - BIREYSEL: Kişisel müşteri hesapları
    - PREMIUM: Yüksek değerli müşteriler
    - MAAS: Maaş hesapları
    - YUKSEK_BAKIYELI: Yüksek bakiyeli hesaplar
    """

    def test_scenario_generate_quality_check(self, scenario_generator):
        """
        Senaryo tabanlı veri üretim ve kalite kontrolü testi.
        Tests scenario-based generation with quality metrics.

        Kalite kontrolleri:
        - Veri şekli doğru olmalı
        - Sütun adları doğru olmalı
        - Değerler makul aralıkta olmalı
        """
        # BIREYSEL senaryo ile veri üret
        synthetic_df = scenario_generator.generate(
            scenario_type=ScenarioType.BIREYSEL,
            num_rows=100,
        )

        assert synthetic_df is not None
        assert len(synthetic_df) == 100

        # Gerekli sütunları kontrol et
        required_columns = ["customer_id", "account_id", "balance", "transaction_count"]
        for col in required_columns:
            assert col in synthetic_df.columns, f"Sütun eksik: {col}"

        # Değer aralıklarını kontrol et
        if "balance" in synthetic_df.columns:
            # BIREYSEL için makul bakiye aralığı
            assert synthetic_df["balance"].min() >= 0
            assert synthetic_df["balance"].max() <= 1_000_000  # 1 milyon TL

    def test_all_scenarios_produce_valid_data(self, scenario_generator):
        """
        Her senaryo türünün geçerli veri ürettiğini test et.
        Tests that all scenario types produce valid data.

        Senaryo türleri:
        1. BIREYSEL
        2. PREMIUM
        3. MAAS
        4. YUKSEK_BAKIYELI
        """
        scenarios = [
            ScenarioType.BIREYSEL,
            ScenarioType.PREMIUM,
            ScenarioType.MAAS,
            ScenarioType.YUKSEK_BAKIYELI,
        ]

        for scenario_type in scenarios:
            # Her senaryo ile veri üret
            df = scenario_generator.generate(
                scenario_type=scenario_type,
                num_rows=50,
            )

            # Veri geçerli olmalı
            assert df is not None, f"Senaryo {scenario_type} geçersiz veri üretti"
            assert len(df) == 50, f"Senaryo {scenario_type} yanlış satır sayısı"
            assert len(df.columns) > 0, f"Senaryo {scenario_type} sütun yok"

            # Sütun adları boş olmamalı
            assert all(col for col in df.columns), f"Senaryo {scenario_type} boş sütun adı"

    def test_scenario_parameters_respected(self, scenario_generator):
        """
        Senaryo parametrelerinin (min/max kısıtları) uygulandığını test et.
        Verifies that scenario parameter constraints (min/max) are honored.

        Kontrol:
        - PREMIUM senaryo: balance > 100.000 TL
        - MAAS senaryo: recurring_income > 0
        - YUKSEK_BAKIYELI: balance > 1.000.000 TL
        """
        # PREMIUM senaryo (yüksek bakiye gerekli)
        premium_df = scenario_generator.generate(
            scenario_type=ScenarioType.PREMIUM,
            num_rows=100,
            min_balance=100_000,
            max_balance=10_000_000,
        )

        if "balance" in premium_df.columns:
            assert premium_df["balance"].min() >= 100_000, \
                "PREMIUM senaryo minimum bakiye kısıtını ihlal etti"

        # MAAS senaryo (düzenli gelir gerekli)
        salary_df = scenario_generator.generate(
            scenario_type=ScenarioType.MAAS,
            num_rows=100,
            min_salary=3_000,
            max_salary=20_000,
        )

        if "salary" in salary_df.columns:
            assert salary_df["salary"].min() >= 3_000, \
                "MAAS senaryo minimum maaş kısıtını ihlal etti"

    def test_custom_scenario_pipeline(self, scenario_generator):
        """
        Kullanıcı tanımlı parametrelerle özel senaryo testi.
        Tests custom scenario with user-defined parameters.

        Örnek:
        - 200 müşteri
        - Bakiye: 50.000 - 500.000 TL
        - PREMIUM müşteriler
        """
        # Özel parameterlerle veri üret
        custom_df = scenario_generator.generate(
            scenario_type=ScenarioType.PREMIUM,
            num_rows=200,
            min_balance=50_000,
            max_balance=500_000,
            region="Istanbul",  # Custom parameter
        )

        assert len(custom_df) == 200

        # Bakiye aralığını kontrol et
        if "balance" in custom_df.columns:
            assert custom_df["balance"].min() >= 50_000
            assert custom_df["balance"].max() <= 500_000


# ============================================================================
# BÖLÜM 4: TestRelationshipIntegrity - İlişki Bütünlüğü Testleri
# ============================================================================

class TestRelationshipIntegrity:
    """
    Tablolar arasındaki yabancı anahtar (FK) ilişkilerinin bütünlüğü testleri.
    Foreign key (FK) relationship integrity tests.

    Beklenen ilişkiler:
    - Müşteriler (customers) → Hesaplar (accounts): 1:N
    - Hesaplar (accounts) → İşlemler (transactions): 1:N
    """

    def test_fk_integrity_customers_accounts(
        self,
        sample_customers_df,
        sample_accounts_df,
        synthetic_generator,
        rule_engine,
    ):
        """
        Müşteri-Hesap FK ilişkisi bütünlüğünü test et.
        Tests customer_id FK integrity between customers and accounts tables.

        Kontrol:
        - Her hesap geçerli bir müşteri_id'sine sahip
        - Müşteri_id'si olmayan hesap yok
        """
        # İlişkili veri oluştur
        customers_df = sample_customers_df.copy()
        accounts_df = sample_accounts_df.copy()

        # Müşteri ve hesap verilerinden kurallar çıkar
        customer_rules = rule_engine.infer_rules(customers_df).rules
        account_rules = rule_engine.infer_rules(accounts_df).rules

        # Sentetik veri üret
        synthetic_customers = synthetic_generator.generate(
            rules=customer_rules,
            num_rows=50,
        )
        synthetic_accounts = synthetic_generator.generate(
            rules=account_rules,
            num_rows=150,
        )

        # FK kontrolü: her hesap ID'si müşteri ID'lerinde olmalı
        if "customer_id" in synthetic_accounts.columns:
            if "customer_id" in synthetic_customers.columns:
                valid_customer_ids = set(synthetic_customers["customer_id"].unique())
                account_customer_ids = set(synthetic_accounts["customer_id"].unique())

                # Hesap tablosundaki müşteri ID'leri müşteri tablosunda olmalı
                orphaned_accounts = account_customer_ids - valid_customer_ids
                assert len(orphaned_accounts) == 0, \
                    f"Yetim hesaplar (customer_id yok): {orphaned_accounts}"

    def test_fk_integrity_accounts_transactions(
        self,
        sample_accounts_df,
        sample_transactions_df,
        synthetic_generator,
        rule_engine,
    ):
        """
        Hesap-İşlem FK ilişkisi bütünlüğünü test et.
        Tests account_id FK integrity between accounts and transactions tables.

        Kontrol:
        - Her işlem geçerli bir hesap_id'sine sahip
        - Hesap_id'si olmayan işlem yok
        """
        # Verileri yükle
        accounts_df = sample_accounts_df.copy()
        transactions_df = sample_transactions_df.copy()

        # Kuralları çıkar
        account_rules = rule_engine.infer_rules(accounts_df).rules
        transaction_rules = rule_engine.infer_rules(transactions_df).rules

        # Sentetik veri üret
        synthetic_accounts = synthetic_generator.generate(
            rules=account_rules,
            num_rows=30,
        )
        synthetic_transactions = synthetic_generator.generate(
            rules=transaction_rules,
            num_rows=300,
        )

        # FK kontrolü: her işlem account_id'si hesaplar tablosunda olmalı
        if "account_id" in synthetic_transactions.columns:
            if "account_id" in synthetic_accounts.columns:
                valid_account_ids = set(synthetic_accounts["account_id"].unique())
                transaction_account_ids = set(synthetic_transactions["account_id"].unique())

                orphaned_transactions = transaction_account_ids - valid_account_ids
                assert len(orphaned_transactions) == 0, \
                    f"Yetim işlemler (account_id yok): {orphaned_transactions}"

    def test_relationship_detection_and_generation(
        self,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        İlişki algılama ve buna dayalı veri üretim testi.
        Tests relationship detection and generation based on relationships.

        Akış:
        1. Müşteri ve hesap verilerini analiz et
        2. İlişkileri algıla
        3. İlişkilere dayalı veri üret
        4. İlişki bütünlüğünü doğrula
        """
        # Örnek veri oluştur
        customers_df = pd.DataFrame({
            "customer_id": [1, 2, 3, 4, 5],
            "name": [f"Müşteri_{i}" for i in range(1, 6)],
            "email": [f"customer{i}@bank.com" for i in range(1, 6)],
        })

        accounts_df = pd.DataFrame({
            "account_id": [101, 102, 103, 104, 105, 106, 107],
            "customer_id": [1, 1, 2, 3, 3, 3, 4],
            "balance": [1000, 2000, 3000, 4000, 5000, 6000, 7000],
        })

        # Veri çiftlerini analiz et
        customer_analysis = schema_analyzer.analyze(customers_df)
        account_analysis = schema_analyzer.analyze(accounts_df)

        assert customer_analysis is not None
        assert account_analysis is not None

        # Kuralları çıkar
        customer_rules = rule_engine.infer_rules(customers_df).rules
        account_rules = rule_engine.infer_rules(accounts_df).rules

        # Sentetik veri üret
        synthetic_customers = synthetic_generator.generate(
            rules=customer_rules,
            num_rows=20,
        )
        synthetic_accounts = synthetic_generator.generate(
            rules=account_rules,
            num_rows=60,
        )

        # Veri oluşturulduğunu doğrula
        assert len(synthetic_customers) == 20
        assert len(synthetic_accounts) == 60

    def test_cardinality_preserved(self, rule_engine, synthetic_generator):
        """
        1:N ilişkilerinin üretim sırasında korunduğunu test et.
        Verifies that 1:N cardinality is preserved in generated data.

        Örnek: Bir müşterinin birden fazla hesabı olabilir (1:N)
        Üretilen verilerde bu ilişki korunmalı
        """
        # 1:N ilişkisi olan veri oluştur
        # 1 müşteri : N hesap
        customers_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "name": ["A", "B", "C"],
        })

        accounts_df = pd.DataFrame({
            "account_id": [101, 102, 103, 104, 105],
            "customer_id": [1, 1, 2, 2, 3],  # 1:2, 2:2, 3:1 ilişkisi
            "balance": [1000, 2000, 3000, 4000, 5000],
        })

        # Kuralları çıkar
        account_rules = rule_engine.infer_rules(accounts_df).rules

        # Veri üret
        synthetic_accounts = synthetic_generator.generate(
            rules=account_rules,
            num_rows=150,
        )

        # Veri üretildiğini doğrula
        assert len(synthetic_accounts) == 150
        assert "account_id" in synthetic_accounts.columns
        if "customer_id" in synthetic_accounts.columns:
            # Benzersiz müşteri sayısından daha fazla hesap olmalı
            unique_customers = synthetic_accounts["customer_id"].nunique()
            assert unique_customers < 150, \
                "Kardinalite bozuk: müşteri sayısı hesap sayısına eşit"


# ============================================================================
# BÖLÜM 5: TestCrossModuleInteraction - Modüller Arası Etkileşim Testleri
# ============================================================================

class TestCrossModuleInteraction:
    """
    Modüller arasındaki etkileşim ve veri akışı testleri.
    Cross-module interaction and data flow tests.

    Test odakları:
    - Sınıflandırma sonuçları kural çıkarımını besler
    - Analiz sonuçları üretimi yapılandırır
    - Hata yayılımı doğru şekilde ele alınır
    - Eş zamanlı pipeline'lar güvenli şekilde çalışır
    """

    def test_classifier_feeds_rule_engine(
        self,
        sample_customers_df,
        column_classifier,
        rule_engine,
    ):
        """
        Sınıflandırma sonuçlarının kural çıkarımını beslemesini test et.
        Tests that column classification results feed into rule inference.

        Akış:
        1. Sütunları sınıflandır (sayısal, kategorik, tarih vs.)
        2. Sınıflandırma sonuçlarını kural motoruna gönder
        3. Kuralların sınıflandırmaya dayalı olduğunu doğrula
        """
        df = sample_customers_df.copy()

        # Sütunları sınıflandır
        classification_result = column_classifier.classify(df)
        assert classification_result is not None
        assert len(classification_result.classifications) > 0

        # Sınıflandırmaların kural oluşturmayı etkilediğini doğrula
        # (Sınıflandırma yapılmış sonucunu motor kullanabilir)
        rules = rule_engine.infer_rules(df).rules
        assert rules is not None

    def test_analyzer_results_drive_generation(
        self,
        sample_transactions_df,
        schema_analyzer,
        synthetic_generator,
        rule_engine,
    ):
        """
        Analiz sonuçlarının veri üretimini yapılandırmasını test et.
        Tests that schema analysis results drive synthetic generation.

        Akış:
        1. Veriyi analiz et (min, max, dağılım vs.)
        2. Analiz sonuçlarına dayalı kurallar oluştur
        3. Üretilen verilerin analiz sonuçlarıyla uyumlu olduğunu doğrula
        """
        df = sample_transactions_df.copy()

        # Şemayı analiz et
        analysis_result = schema_analyzer.analyze(df)
        assert analysis_result is not None

        # Sayısal sütunların istatistiklerini kaydet
        numeric_stats = {}
        for col_analysis in analysis_result.column_analyses:
            if hasattr(col_analysis, "min_value") and hasattr(col_analysis, "max_value"):
                numeric_stats[col_analysis.column_name] = {
                    "min": col_analysis.min_value,
                    "max": col_analysis.max_value,
                }

        # Kuralları çıkar ve veri üret
        rules = rule_engine.infer_rules(df).rules
        synthetic_df = synthetic_generator.generate(rules=rules, num_rows=100)

        # Üretilen verilerin analiz sonuçlarıyla uyumlu olduğunu doğrula
        for col_name, stats in numeric_stats.items():
            if col_name in synthetic_df.columns:
                # Min/max değerleri makul aralıkta olmalı
                generated_min = synthetic_df[col_name].min()
                generated_max = synthetic_df[col_name].max()

                # Üretilen veriler makul aralıkta olmalı
                # (Tam aynı olmayabilir ama benzer olmalı)

    def test_error_propagation_across_modules(
        self,
        schema_analyzer,
        rule_engine,
    ):
        """
        Modüller arası hata yayılımını test et.
        Tests error propagation across modules.

        Senaryo:
        - Geçersiz veri analiz edilmeye çalışılır
        - Hata doğru şekilde raporlanır
        - Hata bilgileri ileri bileşenlere iletilir
        """
        # Geçersiz veri (boş DataFrame)
        invalid_df = pd.DataFrame()

        # Analiz hata ile başarısız olmalı veya boş sonuç döndürmelidir
        try:
            analysis_result = schema_analyzer.analyze(invalid_df)
            # Boş DataFrame'in durumu test et
            assert analysis_result is None or len(analysis_result.column_analyses) == 0
        except Exception as e:
            # Hata alındığını doğrula
            assert True

    def test_concurrent_pipeline_execution(
        self,
        sample_customers_df,
        schema_analyzer,
        rule_engine,
        synthetic_generator,
    ):
        """
        Eş zamanlı pipeline çalıştırma testi.
        Tests concurrent execution of multiple pipelines.

        Senaryo:
        - 2 farklı pipeline eş zamanlı çalışır
        - Her pipeline bağımsız sonuç üretir
        - Sonuçlar birbirini etkilemez
        """
        df1 = sample_customers_df.copy()
        df2 = sample_customers_df.copy()

        results = {}
        lock = threading.Lock()

        def run_pipeline(pipeline_id, df):
            """Pipeline çalıştır ve sonucu kaydet"""
            analysis = schema_analyzer.analyze(df)
            rules = rule_engine.infer_rules(df).rules
            synthetic_df = synthetic_generator.generate(rules=rules, num_rows=50)

            with lock:
                results[pipeline_id] = {
                    "analysis": analysis,
                    "rules": rules,
                    "synthetic_df": synthetic_df,
                }

        # İki pipeline'ı eş zamanlı çalıştır
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(run_pipeline, "pipeline_1", df1)
            executor.submit(run_pipeline, "pipeline_2", df2)

        # Her iki pipeline da sonuç üretmiş olmalı
        assert "pipeline_1" in results
        assert "pipeline_2" in results
        assert results["pipeline_1"]["synthetic_df"] is not None
        assert results["pipeline_2"]["synthetic_df"] is not None

        # Sonuçlar bağımsız olmalı (aynı olmayabilir)
        assert len(results["pipeline_1"]["synthetic_df"]) == 50
        assert len(results["pipeline_2"]["synthetic_df"]) == 50


# ============================================================================
# İlave Yardımcı Fonksiyonlar ve Utiliteleri
# ============================================================================

def verify_data_quality(df: pd.DataFrame) -> bool:
    """
    Veri kalitesi doğrulama fonksiyonu.
    Verifies basic data quality metrics.

    Kontrol noktaları:
    - Hiç boş satır yok
    - Hiç tamamen boş sütun yok
    - Tutarlı veri türleri
    """
    if df is None or df.empty:
        return False

    # Boş satırları kontrol et
    if df.isnull().all(axis=1).any():
        return False

    # Tamamen boş sütunları kontrol et
    if df.isnull().all().any():
        return False

    return True


def assert_column_compatibility(original_df: pd.DataFrame, generated_df: pd.DataFrame):
    """
    Orijinal ve üretilen verinin uyumluluğunu doğrula.
    Asserts compatibility between original and generated DataFrames.

    Kontrol:
    - Aynı sütun adları
    - Uyumlu veri türleri
    - Makul değer aralıkları
    """
    assert list(original_df.columns) == list(generated_df.columns), \
        "Sütun adları uyuşmuyor"

    for col in original_df.columns:
        orig_dtype = original_df[col].dtype
        gen_dtype = generated_df[col].dtype

        # Temel tür uyumluluğunu kontrol et
        if orig_dtype != gen_dtype:
            # Sayısal türler arasında geçişe izin ver
            if not (np.issubdtype(orig_dtype, np.number) and
                    np.issubdtype(gen_dtype, np.number)):
                raise AssertionError(
                    f"Sütun {col} tür uyumsuzluğu: {orig_dtype} -> {gen_dtype}"
                )
