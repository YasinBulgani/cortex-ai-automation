# Platform: BGTS Test Dönüşüm
# Modül: AI-Driven API Keşfif Testleri
# Not: Bu testler LLM bağımlıdır, yavaş çalışır ve non-deterministiktir.
#      CI'da @ai marker'ı ile atlanabilir: pytest -m "not ai"

@ai @slow
Feature: AI ile API Keşfif Testleri
  AI motorunu kullanarak API endpoint'lerini keşifsel olarak test eder.
  Bu testler deterministik değildir; her çalıştırmada farklı sonuç verebilir.

  Background:
    Given kullanıcı ana sayfadadır

  Scenario: AI ile Backend sağlık kontrolü
    When AI "GET http://localhost:8000/health endpoint'ini çağır ve status ok döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: AI ile Auth API doğrulama
    When AI "POST http://localhost:8000/api/v1/auth/login endpoint'ine geçerli kimlik gönder ve token döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: AI ile TSPM proje API erişimi
    When AI "GET http://localhost:8000/api/v1/tspm/projects endpoint'ini geçerli token ile sorgula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: AI ile Engine feature listesi
    When AI "GET http://localhost:5001/api/features/ endpoint'ini çağır ve yanıt döndüğünü doğrula" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır

  Scenario: AI ile BDD senaryo üretimi
    When AI "POST http://localhost:8000/api/v1/tspm/projects/test-project/scenarios/generate-bdd endpoint'ine analiz metni gönder" görevini gerçekleştirir
    Then en az 1 adım başarılı olmalıdır
