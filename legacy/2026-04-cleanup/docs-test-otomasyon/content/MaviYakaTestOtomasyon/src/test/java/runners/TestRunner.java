package runners;

import org.junit.runner.RunWith;

/**
 * Çoklu domain desteği: config'deki domains veya -Ddomains ile belirtilen domainler sırayla çalıştırılır.
 * Tek domain: domains tanımlı değilse data.domain kullanılır.
 * Önceki Allure verileri MultiDomainCucumberRunner tarafından her çalıştırmada temizlenir.
 *
 * Tek feature çalıştırmak: VM option ekleyin: -Dcucumber.features=src/test/resources/features/absence.feature
 * IDE'de "Tek feature (TestRunner)" run config'i bu şekilde ayarlıdır; kopyalayıp path'i değiştirebilirsiniz.

 * Feature yanındaki Run (Cucumber Main) hiç senaryo çalıştırmıyorsa: Run > Edit Configurations > o config'te Working directory = $PROJECT_DIR$ yapın.
 */
@RunWith(MultiDomainCucumberRunner.class)
public class TestRunner {
}