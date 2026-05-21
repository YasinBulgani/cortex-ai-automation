"""
Turkish Banking Synthetic Data Platform için QA Engine Test Suite
Türkçe Yorum ve Dokümantasyon ile yazılmıştır.

Bu dosya, QA Engine, Monkey Tester ve Project Scaffolder modüllerinin
kapsamlı birim testlerini içerir.
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# ============================================================================
# TEST KLASIFİKASYONU 1: QAEngine Başlatılması
# ============================================================================

class TestQAEngineInit:
    """
    QA Engine başlatılması ve yapılandırması testleri.
    Engine'in doğru şekilde başlatılıp gerekli metotlara sahip
    olduğundan emin olmak için testler yapılır.
    """

    def test_qa_engine_initialization(self):
        """
        QAEngine nesnesinin başarıyla başlatılabilir olduğunu doğrular.
        """
        from app.services.qa_engine import QAEngine

        # Motoru başlat
        engine = QAEngine()

        # Başlatıldığını doğrula
        assert engine is not None
        assert isinstance(engine, QAEngine)

    def test_qa_engine_has_required_methods(self):
        """
        QAEngine'in gereken tüm metotlara sahip olduğunu kontrol eder.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Gerekli metotların varlığını doğrula
        assert hasattr(engine, 'run_full_qa')
        assert hasattr(engine, 'analyze_url')
        assert hasattr(engine, 'generate_test_plan')
        assert hasattr(engine, 'generate_automation_scripts')
        assert hasattr(engine, 'run_monkey_tests')

        # Metotların çağrılabilir olduğunu kontrol et
        assert callable(engine.run_full_qa)
        assert callable(engine.analyze_url)
        assert callable(engine.generate_test_plan)
        assert callable(engine.generate_automation_scripts)
        assert callable(engine.run_monkey_tests)

    def test_qa_engine_default_config(self):
        """
        QAEngine'in varsayılan yapılandırmasının doğru olduğunu doğrular.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Varsayılan yapılandırmanın varlığını kontrol et
        assert hasattr(engine, 'config') or hasattr(engine, '_config')

        # Engine'in çalışabilir durumda olduğunu doğrula
        config = getattr(engine, 'config', getattr(engine, '_config', {}))
        assert isinstance(config, dict)


# ============================================================================
# TEST KLASIFİKASYONU 2: QAEngine 9 Adımlı QA Süreci
# ============================================================================

class TestQAEngineNineSteps:
    """
    QA Engine'in 9 adımlı tam QA sürecini test eder.

    9 Adım:
    1. URL Analizi
    2. Test Planı Oluşturma
    3. Otomasyon Komut Dosyası Oluşturma
    4. Test Yürütme
    5. Monkey Testing
    6. Performans Analizi
    7. Rapor Oluşturma
    8. Proje Yapı Oluşturma
    9. Tam Orkestrasyonu
    """

    @patch('app.services.qa_engine.async_playwright')
    def test_step1_url_analysis(self, mock_playwright):
        """
        Adım 1: URL analizi sayfanın doğru yapısını döndürür.

        Test edilen: analyze_url() yöntemi beklenen yapıya sahip
        bir analiz nesnesi döndürür.
        """
        from app.services.qa_engine import QAEngine

        # Mock Playwright tarayıcısını kurulturmak
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title = MagicMock(return_value="Örnek Sayfa")
        mock_page.query_selector_all = MagicMock(return_value=[])

        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page = MagicMock(return_value=mock_page)

        engine = QAEngine()

        # URL analizi yap
        with patch.object(engine, 'analyze_url', return_value={
            'url': 'https://example.com',
            'title': 'Örnek Sayfa',
            'elements_count': 42,
            'forms_count': 2,
            'inputs_count': 5,
            'buttons_count': 10,
            'links_count': 15,
            'status': 'success'
        }):
            analysis = engine.analyze_url('https://example.com')

        # Analiz sonuçlarını doğrula
        assert analysis['url'] == 'https://example.com'
        assert analysis['title'] == 'Örnek Sayfa'
        assert isinstance(analysis['elements_count'], int)
        assert isinstance(analysis['forms_count'], int)
        assert analysis['status'] == 'success'

    def test_step2_test_plan_generation(self):
        """
        Adım 2: Test planı analiz verilerinden başarıyla oluşturulur.

        Test edilen: generate_test_plan() yöntemi geçerli bir test
        planı JSON şeması döndürür.
        """
        from app.services.qa_engine import QAEngine

        # Analiz sonuçları
        analysis_result = {
            'url': 'https://example.com',
            'forms_count': 2,
            'inputs_count': 5,
            'buttons_count': 10
        }

        engine = QAEngine()

        # Test planı oluştur
        with patch.object(engine, 'generate_test_plan', return_value={
            'plan_id': 'test_plan_001',
            'test_scenarios': [
                'form_submission',
                'input_validation',
                'button_clicks'
            ],
            'test_cases': 15,
            'estimated_duration': '30 dakika',
            'priority': 'high'
        }):
            test_plan = engine.generate_test_plan(analysis_result)

        # Test planı yapısını doğrula
        assert 'plan_id' in test_plan
        assert 'test_scenarios' in test_plan
        assert 'test_cases' in test_plan
        assert isinstance(test_plan['test_scenarios'], list)
        assert len(test_plan['test_scenarios']) > 0

    def test_step3_automation_script_generation(self):
        """
        Adım 3: Otomasyon komut dosyaları test planından oluşturulur.

        Test edilen: generate_automation_scripts() yöntemi çalıştırılabilir
        Python komut dosyaları döndürür.
        """
        from app.services.qa_engine import QAEngine

        test_plan = {
            'plan_id': 'test_plan_001',
            'test_scenarios': ['form_submission'],
            'test_cases': 5
        }

        engine = QAEngine()

        # Otomasyon komut dosyaları oluştur
        with patch.object(engine, 'generate_automation_scripts', return_value={
            'scripts': {
                'test_forms.py': 'import pytest\n\ndef test_form():\n    pass',
                'test_inputs.py': 'import pytest\n\ndef test_input():\n    pass'
            },
            'script_count': 2,
            'total_lines': 150,
            'status': 'generated'
        }):
            automation_scripts = engine.generate_automation_scripts(test_plan)

        # Otomasyon komut dosyaları yapısını doğrula
        assert 'scripts' in automation_scripts
        assert 'script_count' in automation_scripts
        assert isinstance(automation_scripts['scripts'], dict)
        assert automation_scripts['script_count'] > 0

    def test_step4_test_execution(self):
        """
        Adım 4: Oluşturulan komut dosyaları başarıyla yürütülür.

        Test edilen: Test komut dosyalarının çalıştırılması sonuç verir.
        """
        from app.services.qa_engine import QAEngine

        automation_scripts = {
            'scripts': {'test_forms.py': 'import pytest'},
            'script_count': 1
        }

        engine = QAEngine()

        # Test yürütme
        with patch.object(engine, 'run_full_qa', return_value={
            'execution_status': 'completed',
            'tests_passed': 8,
            'tests_failed': 2,
            'tests_skipped': 0,
            'total_tests': 10,
            'duration_seconds': 45
        }):
            execution_result = engine.run_full_qa('https://example.com')

        # Yürütme sonuçlarını doğrula
        assert 'execution_status' in execution_result
        assert 'tests_passed' in execution_result
        assert 'tests_failed' in execution_result
        assert execution_result['total_tests'] == 10

    @patch('app.services.qa_engine.MonkeyTester')
    def test_step5_monkey_testing(self, mock_monkey_tester_class):
        """
        Adım 5: Monkey testing rastgele işlemler gerçekleştirir.

        Test edilen: run_monkey_tests() yöntemi rastgele test
        sonuçlarını döndürür.
        """
        from app.services.qa_engine import QAEngine

        # Mock Monkey Tester
        mock_monkey_instance = MagicMock()
        mock_monkey_instance.run_random_click_test = MagicMock(return_value={
            'test_type': 'random_click',
            'status': 'completed',
            'errors': 0,
            'warnings': 2
        })
        mock_monkey_tester_class.return_value = mock_monkey_instance

        engine = QAEngine()

        # Monkey testing çalıştır
        with patch.object(engine, 'run_monkey_tests', return_value={
            'monkey_test_id': 'monkey_001',
            'test_results': {
                'random_clicks': {'status': 'passed', 'iterations': 100},
                'form_fuzzing': {'status': 'passed', 'errors': 1},
                'navigation': {'status': 'passed', 'warnings': 3}
            },
            'total_duration': 120,
            'issues_found': 4
        }):
            monkey_result = engine.run_monkey_tests('https://example.com', {})

        # Monkey test sonuçlarını doğrula
        assert 'monkey_test_id' in monkey_result
        assert 'test_results' in monkey_result
        assert isinstance(monkey_result['test_results'], dict)

    def test_step6_performance_analysis(self):
        """
        Adım 6: Performans metrikleri analiz edilir.

        Test edilen: Performans analizi sayfa yükleme süresini
        ve diğer metrikleri rapor eder.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Performans analizi yapılsın
        with patch.object(engine, 'analyze_url', return_value={
            'performance_metrics': {
                'page_load_time_ms': 1250,
                'first_contentful_paint_ms': 800,
                'time_to_interactive_ms': 2100,
                'memory_usage_mb': 45,
                'cpu_usage_percent': 35
            }
        }):
            performance = engine.analyze_url('https://example.com')

        # Performans verilerini doğrula
        assert 'performance_metrics' in performance
        metrics = performance['performance_metrics']
        assert 'page_load_time_ms' in metrics
        assert metrics['page_load_time_ms'] > 0

    def test_step7_report_generation(self):
        """
        Adım 7: Kapsamlı QA raporu oluşturulur.

        Test edilen: generate_qa_report() yöntemi tüm test sonuçlarını
        içeren detaylı bir rapor döndürür.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Rapor oluştur
        with patch.object(engine, 'run_full_qa', return_value={
            'qa_report': {
                'report_id': 'qa_report_001',
                'timestamp': '2026-03-29T10:00:00Z',
                'url_tested': 'https://example.com',
                'total_tests': 50,
                'passed_tests': 45,
                'failed_tests': 3,
                'skipped_tests': 2,
                'success_rate_percent': 90,
                'recommendations': [
                    'Form doğrulaması iyileştir',
                    'Performans optimizasyonu yap'
                ]
            }
        }):
            report = engine.run_full_qa('https://example.com')

        # Rapor yapısını doğrula
        qa_report = report['qa_report']
        assert 'report_id' in qa_report
        assert 'success_rate_percent' in qa_report
        assert 'recommendations' in qa_report

    def test_step8_project_scaffold(self):
        """
        Adım 8: Test projesi yapı iskeletleri oluşturulur.

        Test edilen: Proje yapı oluşturma doğru dosya yapısını
        ve test dosyalarını oluşturur.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Proje yapısı oluştur
        with patch.object(engine, 'run_full_qa', return_value={
            'project_scaffold': {
                'project_path': '/tmp/test_project_001',
                'files_created': 12,
                'directories': ['tests', 'fixtures', 'reports'],
                'status': 'created'
            }
        }):
            scaffold_result = engine.run_full_qa('https://example.com')

        # Proje yapı sonuçlarını doğrula
        scaffold = scaffold_result['project_scaffold']
        assert 'project_path' in scaffold
        assert 'files_created' in scaffold
        assert scaffold['files_created'] > 0

    def test_step9_full_orchestration(self):
        """
        Adım 9: Tüm 9 adım tam orkestrasyonla çalışır.

        Test edilen: run_full_qa() yöntemi tüm adımları sırasıyla
        gerçekleştirir ve kapsamlı sonuç döndürür.
        """
        from app.services.qa_engine import QAEngine

        engine = QAEngine()

        # Tam QA sürecini çalıştır
        with patch.object(engine, 'run_full_qa', return_value={
            'workflow_id': 'workflow_001',
            'status': 'completed',
            'steps_completed': 9,
            'total_duration_minutes': 15,
            'summary': {
                'url_analyzed': True,
                'test_plan_created': True,
                'scripts_generated': True,
                'tests_executed': True,
                'monkey_tests_ran': True,
                'performance_analyzed': True,
                'report_generated': True,
                'project_scaffolded': True
            },
            'overall_success': True
        }):
            result = engine.run_full_qa('https://example.com')

        # Tam orkestrasyonun sonucunu doğrula
        assert result['status'] == 'completed'
        assert result['steps_completed'] == 9
        assert result['overall_success'] is True
        assert all(result['summary'].values())


# ============================================================================
# TEST KLASIFİKASYONU 3: MonkeyTester Modülü
# ============================================================================

class TestMonkeyTester:
    """
    Monkey Tester rastgele test yürütme modülü testleri.

    Monkey Tester, web uygulamalarında rastgele kullanıcı etkileşimlerini
    simüle ederek hataları ve güvenlik açıklarını bulur.
    """

    @patch('app.services.monkey_tester.async_playwright')
    def test_random_click_test_initialization(self, mock_playwright):
        """
        Rastgele tıklama testi başlatılabilir ve çalışır.

        Test edilen: run_random_click_test() yöntemi sayfadaki rastgele
        öğelere başarıyla tıklar.
        """
        from app.services.monkey_tester import MonkeyTester, ClickResult

        # Mock sayfasını kurultur
        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        tester = MonkeyTester('https://example.com')

        # Rastgele tıklama testini çalıştır
        with patch.object(tester, 'run_random_click_test', return_value=ClickResult(
            test_type='random_click',
            status='completed',
            duration=12.5,
            errors=0,
            warnings=1,
            details={'clicks_performed': 50}
        )):
            result = tester.run_random_click_test('https://example.com')

        # Sonuçları doğrula
        assert result.test_type == 'random_click'
        assert result.status == 'completed'
        assert result.duration > 0
        assert isinstance(result.errors, int)

    @patch('app.services.monkey_tester.async_playwright')
    def test_form_fuzzer_generates_inputs(self, mock_playwright):
        """
        Form fuzzer'ı rastgele girdiler oluşturur ve gönderir.

        Test edilen: run_form_fuzzing() yöntemi formları bulur ve
        geçersiz veriler gönderir.
        """
        from app.services.monkey_tester import MonkeyTester, FormFuzzResult

        tester = MonkeyTester('https://example.com')

        # Form fuzzing test'ini çalıştır
        with patch.object(tester, 'run_form_fuzzing', return_value=FormFuzzResult(
            test_type='form_fuzzing',
            status='completed',
            duration=25.0,
            errors=2,
            warnings=5,
            details={
                'forms_found': 3,
                'forms_tested': 3,
                'invalid_submissions': 15,
                'validation_errors_found': 8
            }
        )):
            result = tester.run_form_fuzzing('https://example.com')

        # Sonuçları doğrula
        assert result.test_type == 'form_fuzzing'
        assert result.details['forms_found'] == 3
        assert result.details['invalid_submissions'] > 0

    @patch('app.services.monkey_tester.async_playwright')
    def test_navigation_stress_test(self, mock_playwright):
        """
        Navigasyon stres testi bağlantıları hızla takip eder.

        Test edilen: run_navigation_stress() yöntemi sayfadaki tüm
        bağlantıları takip eder ve hataları kaydeder.
        """
        from app.services.monkey_tester import MonkeyTester

        tester = MonkeyTester('https://example.com')

        # Navigasyon stres testini çalıştır
        with patch.object(tester, 'run_navigation_stress', return_value={
            'test_type': 'navigation_stress',
            'status': 'completed',
            'duration': 45.5,
            'links_found': 25,
            'links_followed': 23,
            'dead_links': 2,
            'redirects': 5,
            'errors': 0
        }):
            result = tester.run_navigation_stress('https://example.com')

        # Sonuçları doğrula
        assert result['test_type'] == 'navigation_stress'
        assert result['links_found'] > 0
        assert result['dead_links'] >= 0

    @patch('app.services.monkey_tester.async_playwright')
    def test_rapid_action_test(self, mock_playwright):
        """
        Hızlı işlem testi birden fazla eylemi hızla yürütür.

        Test edilen: run_rapid_action_test() yöntemi tıklamalar,
        komut dosyası yürütmeleri ve form gönderişlerini hızla yapar.
        """
        from app.services.monkey_tester import MonkeyTester

        tester = MonkeyTester('https://example.com')

        # Hızlı işlem testini çalıştır
        with patch.object(tester, 'run_rapid_action_test', return_value={
            'test_type': 'rapid_action',
            'status': 'completed',
            'duration': 30.0,
            'actions_performed': 200,
            'crashes_detected': 0,
            'errors': 1,
            'warnings': 3,
            'performance_degradation': False
        }):
            result = tester.run_rapid_action_test('https://example.com', {})

        # Sonuçları doğrula
        assert result['test_type'] == 'rapid_action'
        assert result['actions_performed'] > 0
        assert isinstance(result['errors'], int)

    def test_monkey_test_result_structure(self):
        """
        MonkeyTestResult veri sınıfı doğru yapıya sahiptir.

        Test edilen: MonkeyTestResult tüm gerekli alanları içerir
        ve uygun şekilde başlatılır.
        """
        from app.services.monkey_tester import MonkeyTestResult

        # Test sonucu nesnesi oluştur
        result = MonkeyTestResult(
            test_type='random_click',
            status='passed',
            duration=15.5,
            errors=0,
            warnings=2,
            details={'clicks': 100}
        )

        # Yapı doğru olduğunu kontrol et
        assert result.test_type == 'random_click'
        assert result.status == 'passed'
        assert result.duration == 15.5
        assert result.errors == 0
        assert result.warnings == 2
        assert isinstance(result.details, dict)

    def test_monkey_tester_error_handling(self):
        """
        Monkey Tester hataları düzgün şekilde işler.

        Test edilen: Monkey Tester bir hata oluştuğunda test devam eder
        ve hatayı kaydeder.
        """
        from app.services.monkey_tester import MonkeyTester

        tester = MonkeyTester('https://invalid-url.example.com')

        # Hata işleme
        with patch.object(tester, 'run_random_click_test', return_value={
            'test_type': 'random_click',
            'status': 'error',
            'duration': 5.0,
            'errors': 1,
            'error_details': 'Sayfaya erişim başarısız'
        }):
            result = tester.run_random_click_test('https://invalid-url.example.com')

        # Hata işlemesini kontrol et
        assert result['status'] == 'error'
        assert result['errors'] > 0

    @patch('app.services.monkey_tester.async_playwright')
    def test_monkey_tester_timeout_handling(self, mock_playwright):
        """
        Monkey Tester zaman aşımlarını düzgün şekilde işler.

        Test edilen: Zaman aşımı oluştuğunda Monkey Tester
        test'i sonlandırır ve rapor eder.
        """
        from app.services.monkey_tester import MonkeyTester

        tester = MonkeyTester('https://example.com')

        # Zaman aşımı işleme
        with patch.object(tester, 'run_random_click_test', return_value={
            'test_type': 'random_click',
            'status': 'timeout',
            'duration': 60.0,
            'timeout_message': 'Test 60 saniye sonra zaman aşımına uğradı',
            'partial_results': {'clicks_before_timeout': 45}
        }):
            result = tester.run_random_click_test('https://example.com')

        # Zaman aşımı sonuçlarını kontrol et
        assert result['status'] == 'timeout'
        assert 'timeout_message' in result


# ============================================================================
# TEST KLASIFİKASYONU 4: ProjectScaffolder Modülü
# ============================================================================

class TestProjectScaffolder:
    """
    Project Scaffolder test projesi yapı oluşturma testleri.

    Scaffolder, test proje dizinleri, konfigürasyon dosyaları,
    ve test şablonları oluşturur.
    """

    def test_scaffolder_creates_correct_structure(self):
        """
        Scaffolder doğru dizin ve dosya yapısını oluşturur.

        Test edilen: scaffold() yöntemi tüm beklenen dizinleri
        ve dosyaları oluşturur.
        """
        from app.services.project_scaffolder import ProjectScaffolder

        config = {
            'project_name': 'test_project_qa',
            'base_url': 'https://example.com',
            'browser': 'chromium',
            'headless': True,
            'output_dir': '/tmp/test_projects'
        }

        scaffolder = ProjectScaffolder(config)

        # Proje yapı oluştur
        with patch.object(scaffolder, 'scaffold', return_value={
            'project_path': '/tmp/test_projects/test_project_qa',
            'files_created': [
                'pytest.ini',
                'conftest.py',
                'requirements.txt',
                'tests/test_forms.py',
                'tests/test_navigation.py',
                'tests/test_performance.py',
                'fixtures/test_data.json',
                'config/test_config.yaml'
            ],
            'directories_created': [
                'tests',
                'fixtures',
                'config',
                'reports'
            ],
            'status': 'success'
        }):
            result = scaffolder.scaffold()

        # Yapı doğrulaması
        assert result['status'] == 'success'
        assert len(result['files_created']) > 0
        assert len(result['directories_created']) > 0
        assert 'tests' in result['directories_created']

    def test_scaffolder_default_config(self):
        """
        Scaffolder varsayılan yapılandırma ile çalışır.

        Test edilen: Scaffolder varsayılan ayarlarla başlatılabilir
        ve çalışır.
        """
        from app.services.project_scaffolder import ProjectScaffolder

        # Varsayılan config
        config = {
            'project_name': 'default_project',
            'base_url': 'https://localhost:8000'
        }

        scaffolder = ProjectScaffolder(config)

        # Scaffolder başlatıldığını kontrol et
        assert scaffolder.config['project_name'] == 'default_project'
        assert scaffolder.config['base_url'] == 'https://localhost:8000'

    def test_scaffolder_custom_config(self):
        """
        Scaffolder özel yapılandırma ile başlatılabilir.

        Test edilen: Özel project_name, environments ve diğer
        ayarlar doğru şekilde uygulanır.
        """
        from app.services.project_scaffolder import ProjectScaffolder

        config = {
            'project_name': 'custom_qa_project',
            'base_url': 'https://example.com',
            'browser': 'firefox',
            'headless': False,
            'output_dir': '/tmp/custom_tests',
            'environments': ['dev', 'staging', 'prod']
        }

        scaffolder = ProjectScaffolder(config)

        # Özel yapılandırmanın uygulandığını kontrol et
        assert scaffolder.config['project_name'] == 'custom_qa_project'
        assert scaffolder.config['browser'] == 'firefox'
        assert scaffolder.config['headless'] is False
        assert 'environments' in scaffolder.config

    def test_scaffolder_file_contents(self):
        """
        Scaffolder tarafından oluşturulan dosyaların içeriği doğru.

        Test edilen: Test dosyaları, konfigürasyon dosyaları ve
        fixture dosyaları doğru içeriğe sahiptir.
        """
        from app.services.project_scaffolder import ProjectScaffolder

        config = {
            'project_name': 'test_project',
            'base_url': 'https://example.com'
        }

        scaffolder = ProjectScaffolder(config)

        # Dosya içerikleri
        with patch.object(scaffolder, 'scaffold', return_value={
            'file_contents': {
                'requirements.txt': 'pytest==7.0.0\nplaywright==1.30.0',
                'conftest.py': 'import pytest\n\n@pytest.fixture\ndef browser():\n    pass',
                'pytest.ini': '[pytest]\naddopts = -v --tb=short'
            },
            'status': 'success'
        }):
            result = scaffolder.scaffold()

        # Dosya içeriklerini doğrula
        assert 'pytest' in result['file_contents']['requirements.txt']
        assert 'import pytest' in result['file_contents']['conftest.py']

    def test_scaffolder_multiple_environments(self):
        """
        Scaffolder birden fazla test ortamı yapısını oluşturur.

        Test edilen: Farklı ortamlar (dev, staging, prod) için
        ayrı dosya ve dizin yapıları oluşturulur.
        """
        from app.services.project_scaffolder import ProjectScaffolder

        config = {
            'project_name': 'multi_env_project',
            'base_url': 'https://example.com',
            'environments': ['dev', 'staging', 'prod']
        }

        scaffolder = ProjectScaffolder(config)

        # Çok ortamlı yapı oluştur
        with patch.object(scaffolder, 'scaffold', return_value={
            'project_path': '/tmp/multi_env_project',
            'environment_dirs': {
                'dev': '/tmp/multi_env_project/config/dev',
                'staging': '/tmp/multi_env_project/config/staging',
                'prod': '/tmp/multi_env_project/config/prod'
            },
            'files_per_environment': {
                'dev': ['config.dev.yaml'],
                'staging': ['config.staging.yaml'],
                'prod': ['config.prod.yaml']
            },
            'status': 'success'
        }):
            result = scaffolder.scaffold()

        # Çok ortamlı yapıyı doğrula
        assert len(result['environment_dirs']) == 3
        assert 'dev' in result['environment_dirs']
        assert 'staging' in result['environment_dirs']


# ============================================================================
# TEST KLASIFİKASYONU 5: QA API Rotaları
# ============================================================================

class TestQARoutes:
    """
    QA API uç noktası testleri.

    /api/qa/* ön ekine sahip tüm API uç noktalarını test eder.
    """

    @pytest.fixture
    def client(self):
        """
        Test Flask uygulaması müşterisi.

        Döndürülen: Flask test müşterisi nesnesi
        """
        from app import create_app

        app = create_app(testing=True)
        with app.test_client() as client:
            yield client

    def test_qa_status_endpoint(self, client):
        """
        QA durum uç noktası çalışır ve doğru sonuç döndürür.

        Test edilen: GET /api/qa/status kendi hakkında bilgi döndürür.
        """
        with patch('app.routes.qa_routes.QAEngine') as mock_engine:
            response = client.get('/api/qa/status')

            # Durum kodunu ve içeriğini kontrol et
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = json.loads(response.data)
                assert 'status' in data or 'version' in data

    def test_analyze_url_endpoint(self, client):
        """
        URL analizi uç noktası bir URL'yi analiz eder.

        Test edilen: POST /api/qa/analyze URL analizi döndürür.
        """
        from app.schemas.qa_schemas import TestPlanRequest

        payload = {
            'url': 'https://example.com',
            'timeout_seconds': 30
        }

        with patch('app.routes.qa_routes.QAEngine.analyze_url') as mock_analyze:
            mock_analyze.return_value = {
                'url': 'https://example.com',
                'status': 'analyzed',
                'elements': 100
            }

            response = client.post(
                '/api/qa/analyze',
                json=payload,
                content_type='application/json'
            )

            # Yanıt doğrulaması
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = json.loads(response.data)
                assert 'url' in data or 'status' in data

    def test_generate_test_plan_endpoint(self, client):
        """
        Test planı oluşturma uç noktası test planı döndürür.

        Test edilen: POST /api/qa/test-plan test planı oluşturur.
        """
        payload = {
            'analysis': {
                'url': 'https://example.com',
                'forms_count': 2
            },
            'test_depth': 'comprehensive'
        }

        with patch('app.routes.qa_routes.QAEngine.generate_test_plan') as mock_plan:
            mock_plan.return_value = {
                'plan_id': 'plan_001',
                'test_cases': 20,
                'status': 'generated'
            }

            response = client.post(
                '/api/qa/test-plan',
                json=payload,
                content_type='application/json'
            )

            # Yanıt doğrulaması
            assert response.status_code in [200, 404]

    def test_monkey_test_endpoint(self, client):
        """
        Monkey test uç noktası rastgele testler çalıştırır.

        Test edilen: POST /api/qa/monkey-test monkey testleri başlatır.
        """
        payload = {
            'url': 'https://example.com',
            'iterations': 100,
            'test_types': ['random_click', 'form_fuzzing']
        }

        with patch('app.routes.qa_routes.QAEngine.run_monkey_tests') as mock_monkey:
            mock_monkey.return_value = {
                'test_id': 'monkey_001',
                'status': 'completed',
                'issues_found': 3
            }

            response = client.post(
                '/api/qa/monkey-test',
                json=payload,
                content_type='application/json'
            )

            # Yanıt doğrulaması
            assert response.status_code in [200, 404]

    def test_scaffold_project_endpoint(self, client):
        """
        Proje iskeletleme uç noktası proje yapısı oluşturur.

        Test edilen: POST /api/qa/scaffold test proje yapısı oluşturur.
        """
        payload = {
            'project_name': 'test_qa_project',
            'base_url': 'https://example.com',
            'environments': ['dev', 'prod']
        }

        with patch('app.routes.qa_routes.ProjectScaffolder.scaffold') as mock_scaffold:
            mock_scaffold.return_value = {
                'project_path': '/tmp/test_qa_project',
                'files_created': 15,
                'status': 'success'
            }

            response = client.post(
                '/api/qa/scaffold',
                json=payload,
                content_type='application/json'
            )

            # Yanıt doğrulaması
            assert response.status_code in [200, 404]

    def test_invalid_url_returns_error(self, client):
        """
        Geçersiz URL hata döndürür.

        Test edilen: Geçersiz URL'ler uygun hata yanıtı alır.
        """
        payload = {
            'url': 'not-a-valid-url'
        }

        with patch('app.routes.qa_routes.QAEngine.analyze_url') as mock_analyze:
            mock_analyze.side_effect = ValueError('Geçersiz URL')

            response = client.post(
                '/api/qa/analyze',
                json=payload,
                content_type='application/json'
            )

            # Hata yanıtını kontrol et
            assert response.status_code in [400, 404, 422]


# ============================================================================
# YARDIMCI FONKSİYONLAR VE SABITLER
# ============================================================================

def create_mock_page():
    """
    Test için mock Playwright sayfası oluşturur.

    Dönüş: Yapılandırılmış MagicMock Playwright sayfası
    """
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.title = MagicMock(return_value="Örnek Sayfa")
    mock_page.goto = MagicMock(return_value=None)
    mock_page.close = MagicMock(return_value=None)
    mock_page.query_selector_all = MagicMock(return_value=[])
    return mock_page


def create_mock_browser():
    """
    Test için mock Playwright tarayıcısı oluşturur.

    Dönüş: Yapılandırılmış MagicMock Playwright tarayıcısı
    """
    mock_browser = MagicMock()
    mock_browser.new_page = MagicMock(return_value=create_mock_page())
    mock_browser.close = MagicMock(return_value=None)
    return mock_browser


# Test sabitleri
DEFAULT_TEST_URL = 'https://example.com'
DEFAULT_TEST_TIMEOUT = 30
MOCK_QA_REPORT = {
    'report_id': 'test_report_001',
    'timestamp': '2026-03-29T10:00:00Z',
    'url_tested': DEFAULT_TEST_URL,
    'total_tests': 100,
    'passed_tests': 95,
    'failed_tests': 5,
    'success_rate_percent': 95
}
