package utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.util.Map;

/**
 * Registry that loads named SQL queries from {@code sqlQueries/sql.json} on the classpath.
 *
 * <p>The JSON file is a flat {@code Map<String, String>} where each key is a logical
 * query name and the value is the full SQL statement (may include {@code ?} placeholders
 * for JDBC {@code PreparedStatement} binding).
 *
 * <p>Queries are loaded once at class-init time via classpath lookup — this is safe for
 * Maven {@code test} and {@code package} phases, and for IDE runs, because the resource
 * ends up on the classpath regardless of the working directory.  (The previous
 * implementation used a hardcoded relative file path which broke when the working
 * directory differed from the project root.)
 *
 * <p>Thread safety: {@link #queries} is populated once during static initialisation
 * and never mutated — safe for concurrent reads without synchronisation.
 */
public class QueryManager {

    private static final Map<String, String> queries;

    static {
        try (InputStream in = QueryManager.class.getClassLoader()
                .getResourceAsStream("sqlQueries/sql.json")) {
            if (in == null) {
                throw new RuntimeException(
                        "sqlQueries/sql.json not found on classpath. "
                        + "Ensure src/main/resources/sqlQueries/sql.json exists.");
            }
            ObjectMapper mapper = new ObjectMapper();
            queries = mapper.readValue(in, new TypeReference<Map<String, String>>() {});
        } catch (Exception e) {
            throw new RuntimeException("Failed to load sqlQueries/sql.json", e);
        }
    }

    /**
     * Returns the SQL query registered under {@code key}.
     *
     * @param key the logical query name defined in sql.json
     * @return the SQL string (never {@code null})
     * @throws IllegalArgumentException if no query is registered for {@code key}
     */
    public static String getQuery(String key) {
        String query = queries.get(key);
        if (query == null) {
            throw new IllegalArgumentException("No SQL query found for key: '" + key
                    + "'. Check sqlQueries/sql.json for valid keys.");
        }
        return query;
    }
}
