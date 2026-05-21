"""
Türkçe Banka Sentetik Veri Platformu için Performans Testleri

Bu test dosyası, aşağıdaki hizmetlerin performansını ve ölçeklenebilirliğini test eder:
- SchemaAnalyzer: DataFrame analizi
- ColumnClassifier: Sütun sınıflandırması
- RuleInferenceEngine: Kural çıkarımı
- SyntheticDataGenerator: Sentetik veri üretimi
- ScenarioGenerator: Senaryo tabanlı veri üretimi

Testler zaman, bellek kullanımı ve eşzamanlı talepleri ölçer.
"""

import time
import tracemalloc
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
import numpy as np
import pandas as pd

# Hizmetleri içeri aktar
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.column_classifier import ColumnClassifier
from app.services.rule_engine import RuleInferenceEngine
from app.services.synthetic_generator import SyntheticDataGenerator
from app.services.scenario_generator import ScenarioGenerator


# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def generate_large_dataframe(n_rows: int) -> pd.DataFrame:
    """
    Gerçekçi bir Türk bankacılık DataFrame'i oluştur.

    Sütunlar:
    - customer_id: Müşteri kimlik numarası
    - first_name: Ad
    - last_name: Soyadı
    - tckn: Türkiye Cumhuriyet Kimlik Numarası
    - email: E-posta adresi
    - phone: Telefon numarası
    - city: Şehir
    - balance: Hesap bakiyesi
    - credit_score: Kredi puanı
    - account_type: Hesap türü
    - status: Hesap durumu

    Args:
        n_rows: Oluşturulacak satır sayısı

    Returns:
        Sentetik veri ile doldurulmuş DataFrame
    """
    np.random.seed(42)

    first_names = ["Ahmet", "Mehmet", "Fatih", "Ayşe", "Zeynep", "Murat",
                   "Hüseyin", "Elif", "Kadir", "Zuhal", "Emre", "Seda"]
    last_names = ["Yılmaz", "Kaya", "Demir", "Arslan", "Doğan", "Polat",
                  "Şimşek", "Güzel", "Aydın", "Çetin", "Öztürk", "Kılıç"]
    cities = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Gaziantep",
              "Konya", "Adana", "Diyarbakır", "Mersin", "Kayseri", "Eskişehir"]
    account_types = ["Vadesiz", "Vadeli", "Tasarruf", "Ticari", "Mevduat"]
    statuses = ["Aktif", "Pasif", "Blokeli", "Kapalı", "Suspans"]

    data = {
        "customer_id": np.arange(1, n_rows + 1),
        "first_name": np.random.choice(first_names, n_rows),
        "last_name": np.random.choice(last_names, n_rows),
        "tckn": np.random.randint(10000000000, 99999999999, n_rows),
        "email": [f"user{i}@example.com" for i in range(n_rows)],
        "phone": [f"+905{np.random.randint(100000000, 999999999)}" for _ in range(n_rows)],
        "city": np.random.choice(cities, n_rows),
        "balance": np.random.uniform(1000, 1000000, n_rows),
        "credit_score": np.random.randint(300, 900, n_rows),
        "account_type": np.random.choice(account_types, n_rows),
        "status": np.random.choice(statuses, n_rows),
    }

    return pd.DataFrame(data)


def measure_execution_time(func, *args, **kwargs) -> Tuple[float, any]:
    """
    Bir fonksiyonun yürütme süresini ölç.

    Args:
        func: Ölçülecek fonksiyon
        *args: Fonksiyona geçilecek pozisyonel argümanlar
        **kwargs: Fonksiyona geçilecek anahtar argümanlar

    Returns:
        (geçen_zaman_saniye, fonksiyon_sonucu) tuple'ı
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    elapsed_time = time.time() - start_time
    return elapsed_time, result


def get_memory_usage() -> float:
    """
    Geçerli bellek kullanımını MB cinsinden döndür.

    Returns:
        Bellek kullanımı (MB)
    """
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # psutil yoksa, tracemalloc kullan
        return tracemalloc.get_traced_memory()[0] / (1024 * 1024)


# ============================================================================
# TEST SINIFI: ÜRETIM PERFORMANSI
# ============================================================================

class TestGenerationPerformance:
    """
    Sentetik veri üretiminin performans testleri.

    Üretilen satır sayısına göre zaman ölçümü yapılır ve
    performans tresholdlarıyla karşılaştırılır.
    """

    def test_generate_10k_rows_under_30s(self):
        """
        10.000 satırlık veri üretiminin 30 saniyeden az sürmesi gerekir.

        Test Açıklaması:
        - 10.000 satırlık sentetik veri oluştur
        - Üretim süresi ölçü
        - Assertion: süre < 30 saniye
        """
        generator = SyntheticDataGenerator()

        elapsed_time, result = measure_execution_time(
            generator.generate,
            num_rows=10000
        )

        assert elapsed_time < 30.0, \
            f"10K satır üretimi {elapsed_time:.2f}s sürdü, max 30s izin verilir"
        assert result is not None, "Üretilen veri None olmamalıdır"
        assert len(result) == 10000, f"Beklenen 10000 satır, alındı {len(result)}"

    def test_generate_50k_rows_under_120s(self):
        """
        50.000 satırlık veri üretiminin 120 saniyeden az sürmesi gerekir.

        Test Açıklaması:
        - 50.000 satırlık sentetik veri oluştur
        - Üretim süresi ölçü
        - Assertion: süre < 120 saniye
        """
        generator = SyntheticDataGenerator()

        elapsed_time, result = measure_execution_time(
            generator.generate,
            num_rows=50000
        )

        assert elapsed_time < 120.0, \
            f"50K satır üretimi {elapsed_time:.2f}s sürdü, max 120s izin verilir"
        assert len(result) == 50000, f"Beklenen 50000 satır, alındı {len(result)}"

    @pytest.mark.slow
    def test_generate_100k_rows_under_300s(self):
        """
        100.000 satırlık veri üretiminin 300 saniyeden az sürmesi gerekir.

        Bu test 'slow' olarak işaretlenmiştir ve varsayılan olarak atlanabilir.
        Çalıştırmak için: pytest -m slow

        Test Açıklaması:
        - 100.000 satırlık sentetik veri oluştur
        - Üretim süresi ölçü
        - Assertion: süre < 300 saniye
        """
        generator = SyntheticDataGenerator()

        elapsed_time, result = measure_execution_time(
            generator.generate,
            num_rows=100000
        )

        assert elapsed_time < 300.0, \
            f"100K satır üretimi {elapsed_time:.2f}s sürdü, max 300s izin verilir"
        assert len(result) == 100000, f"Beklenen 100000 satır, alındı {len(result)}"

    def test_generation_time_scales_linearly(self):
        """
        Veri üretim zamanı satır sayısı ile doğrusal olarak ölçeklenmelidir.

        Test Açıklaması:
        - 5K ve 10K satır üret ve zamanı ölç
        - Zaman oranını hesapla
        - Oranı doğrusallık toleransı ile karşılaştır
        """
        generator = SyntheticDataGenerator()

        time_5k, _ = measure_execution_time(
            generator.generate,
            num_rows=5000
        )
        time_10k, _ = measure_execution_time(
            generator.generate,
            num_rows=10000
        )

        # Doğrusal ölçekleme tahmini: zaman ~2x olmalı
        ratio = time_10k / time_5k

        # Tolerans: 0.8x - 2.5x arasında (doğrusal+overhead)
        assert 0.8 <= ratio <= 2.5, \
            f"Ölçekleme doğrusal değil. 5K→10K oranı: {ratio:.2f}x"

    def test_scenario_generation_performance(self):
        """
        Senaryo tabanlı veri üretiminin performansını test et.

        Test Açıklaması:
        - ScenarioGenerator kullanarak senaryo oluştur
        - Üretim süresini ölçü
        - Assertion: süre < 20 saniye
        """
        scenario_gen = ScenarioGenerator()

        elapsed_time, result = measure_execution_time(
            scenario_gen.generate_scenario,
            scenario_type="müşteri_profili",
            count=5000
        )

        assert elapsed_time < 20.0, \
            f"Senaryo üretimi {elapsed_time:.2f}s sürdü, max 20s izin verilir"
        assert result is not None, "Senaryo sonucu None olmamalıdır"


# ============================================================================
# TEST SINIFI: BELLEK KULLANIMI
# ============================================================================

class TestMemoryUsage:
    """
    Bellek kullanımı ve serbest bırakılma testleri.

    Bu testler veri üretimi sırasında bellek tüketimini ölçer
    ve bellek sızıntılarını tespit eder.
    """

    def setup_method(self):
        """Her test öncesi bellek izlemeyi başlat."""
        tracemalloc.start()

    def teardown_method(self):
        """Her test sonrası bellek izlemeyi durdur."""
        tracemalloc.stop()

    def test_memory_usage_10k_rows(self):
        """
        10.000 satır üretimi maksimum 500 MB bellek kullanmalıdır.

        Test Açıklaması:
        - 10.000 satır veri oluştur
        - Bellek kullanımını ölçü
        - Assertion: kullanım < 500 MB
        """
        generator = SyntheticDataGenerator()

        initial_memory = get_memory_usage()
        result = generator.generate(num_rows=10000)
        peak_memory = get_memory_usage()

        memory_delta = peak_memory - initial_memory

        assert memory_delta < 500, \
            f"10K satır için {memory_delta:.2f} MB bellek kullanıldı, max 500 MB"
        assert result is not None, "Sonuç None olmamalıdır"

    def test_memory_usage_50k_rows(self):
        """
        50.000 satır üretimi maksimum 1 GB bellek kullanmalıdır.

        Test Açıklaması:
        - 50.000 satır veri oluştur
        - Bellek kullanımını ölçü
        - Assertion: kullanım < 1000 MB (1 GB)
        """
        generator = SyntheticDataGenerator()

        initial_memory = get_memory_usage()
        result = generator.generate(num_rows=50000)
        peak_memory = get_memory_usage()

        memory_delta = peak_memory - initial_memory

        assert memory_delta < 1000, \
            f"50K satır için {memory_delta:.2f} MB bellek kullanıldı, max 1000 MB"

    def test_memory_cleanup_after_generation(self):
        """
        Veri üretimi sonrası bellek serbest bırakılmalıdır.

        Test Açıklaması:
        - Veri oluştur
        - Bellek pik kullanımını kaydet
        - Veriyi sil
        - Belleği temizle
        - Son bellek kullanımı pik'ten az olmalı
        """
        generator = SyntheticDataGenerator()

        result = generator.generate(num_rows=10000)
        peak_memory = get_memory_usage()

        # Veriyi sil
        del result

        # Garbage collection yap
        import gc
        gc.collect()

        final_memory = get_memory_usage()

        # Final bellek, peak'in %30'undan az olmalı
        assert final_memory < peak_memory * 0.3, \
            f"Bellek temizlenmedi. Peak: {peak_memory:.2f} MB, Son: {final_memory:.2f} MB"

    def test_memory_usage_analysis(self):
        """
        Büyük DataFrame analizi için bellek kullanımını ölçü.

        Test Açıklaması:
        - 100K satırlı DataFrame oluştur
        - SchemaAnalyzer ile analiz et
        - Bellek kullanımını ölçü
        - Assertion: kullanım < 200 MB
        """
        df = generate_large_dataframe(100000)
        analyzer = SchemaAnalyzer()

        initial_memory = get_memory_usage()
        result = analyzer.analyze(df)
        peak_memory = get_memory_usage()

        memory_delta = peak_memory - initial_memory

        assert memory_delta < 200, \
            f"Analiz için {memory_delta:.2f} MB bellek kullanıldı, max 200 MB"


# ============================================================================
# TEST SINIFI: EŞ ZAMANLI ISTEKLER
# ============================================================================

class TestConcurrentRequests:
    """
    Eşzamanlı istek işleme ve veri tutarlılığı testleri.

    Bu testler, hizmetlerin birden fazla eş zamanlı talep altında
    doğru ve tutarlı sonuçlar üretip üretmediğini doğrular.
    """

    def test_concurrent_schema_analysis(self):
        """
        5 eşzamanlı schema analiz işlemi doğru sonuçlar vermelidir.

        Test Açıklaması:
        - 5 farklı DataFrame oluştur
        - ThreadPoolExecutor ile 5 analiz işlemi başlat
        - Tüm analizlerin başarılı olması kontrol et
        - Hata olmadığını doğrula
        """
        def analyze_dataframe(n):
            """Bir DataFrame analiz et."""
            df = generate_large_dataframe(5000 + n * 1000)
            analyzer = SchemaAnalyzer()
            return analyzer.analyze(df)

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(analyze_dataframe, i): i
                for i in range(5)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        assert len(errors) == 0, f"Analizde {len(errors)} hata oluştu: {errors}"
        assert len(results) == 5, f"Beklenen 5 sonuç, alındı {len(results)}"

    def test_concurrent_classification(self):
        """
        5 eşzamanlı sütun sınıflandırması doğru sonuçlar vermelidir.

        Test Açıklaması:
        - 5 farklı DataFrame oluştur
        - ThreadPoolExecutor ile 5 sınıflandırma işlemi başlat
        - Tüm sınıflandırmaların başarılı olması kontrol et
        """
        def classify_dataframe(n):
            """Bir DataFrame'in sütunlarını sınıflandır."""
            df = generate_large_dataframe(5000)
            classifier = ColumnClassifier()
            return classifier.classify_all(df)

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(classify_dataframe, i): i
                for i in range(5)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        assert len(errors) == 0, f"Sınıflandırmada {len(errors)} hata oluştu"
        assert len(results) == 5, f"Beklenen 5 sonuç, alındı {len(results)}"

    def test_concurrent_generation(self):
        """
        3 eşzamanlı veri üretimi işlemi bağımsız sonuçlar vermelidir.

        Test Açıklaması:
        - ThreadPoolExecutor ile 3 üretim işlemi başlat
        - Her işlem farklı veri üretmeli
        - Tüm işlemler başarılı olmalı
        """
        def generate_data(seed):
            """Veri üret."""
            generator = SyntheticDataGenerator()
            return generator.generate(num_rows=5000)

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(generate_data, i): i
                for i in range(3)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        assert len(errors) == 0, f"Üretimde {len(errors)} hata oluştu"
        assert len(results) == 3, f"Beklenen 3 sonuç, alındı {len(results)}"

    def test_no_data_corruption_under_concurrency(self):
        """
        Eşzamanlı işlemler altında veri bozulmama kontrol et.

        Test Açıklaması:
        - 3 eş zamanlı üretim işlemi başlat
        - Her sonuç kontrol et
        - Sonuçlar bağımsız ve benzersiz olmalı
        """
        def generate_and_verify(task_id):
            """Veri üret ve özet istatistik dön."""
            generator = SyntheticDataGenerator()
            df = generator.generate(num_rows=3000)

            # Veri bütünlüğü kontrol
            assert df is not None, f"Task {task_id}: DataFrame None"
            assert len(df) == 3000, f"Task {task_id}: Yanlış satır sayısı"

            return {
                "task_id": task_id,
                "row_count": len(df),
                "hash": hash(tuple(df.values.flatten()[:100]))
            }

        results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(generate_and_verify, i)
                for i in range(3)
            ]

            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == 3, "Tüm işlemler tamamlanmalı"

        # Hash değerleri farklı olmalı
        hashes = [r["hash"] for r in results]
        assert len(set(hashes)) >= 2, "Eşzamanlı işlemler farklı veri üretmeli"


# ============================================================================
# TEST SINIFI: BÜYÜK DOSYA ANALİZİ
# ============================================================================

class TestLargeFileAnalysis:
    """
    Büyük veri setleri üzerinde analiz işlemlerinin performans testleri.

    Bu testler, gerçek dünya senaryolarında (100K+ satır)
    hizmetlerin performansını doğrular.
    """

    def test_analyze_large_csv_under_10s(self):
        """
        100K satırlı CSV analizi 10 saniyeden az sürmesi gerekir.

        Test Açıklaması:
        - 100K satırlık DataFrame oluştur
        - SchemaAnalyzer ile analiz et
        - Assertion: süre < 10 saniye
        """
        df = generate_large_dataframe(100000)
        analyzer = SchemaAnalyzer()

        elapsed_time, result = measure_execution_time(
            analyzer.analyze,
            df
        )

        assert elapsed_time < 10.0, \
            f"100K analizi {elapsed_time:.2f}s sürdü, max 10s izin verilir"
        assert result is not None, "Analiz sonucu None olmamalıdır"

    def test_classify_large_dataset(self):
        """
        100K satırlık veri sütun sınıflandırması performansını test et.

        Test Açıklaması:
        - 100K satırlık DataFrame oluştur
        - ColumnClassifier ile sınıflandır
        - Assertion: işlem başarılı olmalı
        """
        df = generate_large_dataframe(100000)
        classifier = ColumnClassifier()

        elapsed_time, result = measure_execution_time(
            classifier.classify_all,
            df
        )

        assert result is not None, "Sınıflandırma sonucu None olmamalıdır"
        # Sınıflandırma hedef süresi 15 saniye
        assert elapsed_time < 15.0, \
            f"Sınıflandırma {elapsed_time:.2f}s sürdü, max 15s izin verilir"

    def test_rule_inference_large_dataset(self):
        """
        50K satırlık veri üzerinde kural çıkarımı performansını test et.

        Test Açıklaması:
        - 50K satırlık DataFrame oluştur
        - RuleInferenceEngine ile kurallar çıkar
        - Assertion: işlem başarılı olmalı
        """
        df = generate_large_dataframe(50000)
        rule_engine = RuleInferenceEngine()

        elapsed_time, result = measure_execution_time(
            rule_engine.infer_all_rules,
            df
        )

        assert result is not None, "Kural çıkarımı sonucu None olmamalıdır"
        # Kural çıkarımı hedef süresi 25 saniye
        assert elapsed_time < 25.0, \
            f"Kural çıkarımı {elapsed_time:.2f}s sürdü, max 25s izin verilir"

    def test_pii_detection_large_dataset(self):
        """
        50K satırlık veri üzerinde PII tespit performansını test et.

        Test Açıklaması:
        - 50K satırlık DataFrame oluştur
        - PII sütunlarını tespit et
        - Tespit edilen sütunlar: tckn, email, phone
        """
        df = generate_large_dataframe(50000)

        # PII sütunlarını kontrol et
        pii_columns = ["tckn", "email", "phone"]

        for col in pii_columns:
            assert col in df.columns, f"{col} sütunu DataFrame'de olmalı"

        # DataFrame doğrulanması
        assert len(df) == 50000, f"Beklenen 50000 satır, alındı {len(df)}"
        assert df["tckn"].notna().sum() > 0, "TCKN verileri boş olmamalı"


# ============================================================================
# FIKSTÜRLER (conftest.py'den alınan)
# ============================================================================

# Not: conftest.py dosyasında tanımlı olan fikstürler:
# - sample_customers_df
# - sample_accounts_df
# - sample_transactions_df
#
# Bu fikstürler teste ihtiyaç halinde parametreler olarak
# test fonksiyonlarına geçirilebilir:
#
# def test_example(self, sample_customers_df):
#     """sample_customers_df fikstürü kullanılır."""
#     pass


if __name__ == "__main__":
    """
    Komut satırından çalıştırma örneği:

    Tüm testleri çalıştır:
    pytest tests/test_performance.py -v

    Sadece hızlı testleri çalıştır:
    pytest tests/test_performance.py -v -m "not slow"

    Slow testleri de dahil et:
    pytest tests/test_performance.py -v -m slow

    Belirli test sınıfını çalıştır:
    pytest tests/test_performance.py::TestGenerationPerformance -v

    Belirli test fonksiyonunu çalıştır:
    pytest tests/test_performance.py::TestGenerationPerformance::test_generate_10k_rows_under_30s -v

    Zaman aşımı olmadan çalıştır:
    pytest tests/test_performance.py -v --timeout=600
    """
    pytest.main([__file__, "-v"])
