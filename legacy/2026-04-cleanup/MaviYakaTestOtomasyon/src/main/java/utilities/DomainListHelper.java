package utilities;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Domain listesini config veya -Ddomains parametresinden okur.
 * Öncelik: 1) System property (-Ddomains), 2) config.properties (domains)
 * Hiçbiri yoksa tek domain: data.domain
 */
public class DomainListHelper {

    private static final String DOMAINS_KEY = "domains";

    /**
     * Çalıştırılacak domain listesini döner.
     *
     * @return Domain listesi (boş olmaz, en az 1 domain)
     */
    public static List<String> getDomainList() {
        String domainsStr = System.getProperty(DOMAINS_KEY);
        if (domainsStr == null || domainsStr.isBlank()) {
            domainsStr = ConfigReader.get(DOMAINS_KEY);
        }
        if (domainsStr == null || domainsStr.isBlank()) {
            // Tek domain modu: data.domain kullan
            String singleDomain = System.getProperty("data.domain");
            if (singleDomain == null || singleDomain.isBlank()) {
                singleDomain = ConfigReader.get("data.domain");
            }
            if (singleDomain == null || singleDomain.isBlank()) {
                singleDomain = "girit";
            }
            return Arrays.asList(singleDomain.trim());
        }

        return Arrays.stream(domainsStr.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toList());
    }

    /**
     * Çoklu domain modunda mı? (2+ domain)
     */
    public static boolean isMultiDomainMode() {
        return getDomainList().size() > 1;
    }
}
