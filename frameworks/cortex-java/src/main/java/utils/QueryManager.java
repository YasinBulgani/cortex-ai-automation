package utils;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Loads SQL queries from src/main/resources/sqlQueries/sql.json.
 * Used by PwDbMethods.executeSqlFromJson(key, params).
 */
public class QueryManager {

    private static final Map<String, String> queries = loadQueries();

    @SuppressWarnings("unchecked")
    private static Map<String, String> loadQueries() {
        File f = new File("src/main/resources/sqlQueries/sql.json");
        if (!f.exists()) {
            System.err.println("[QueryManager] sql.json not found, returning empty map");
            return new HashMap<>();
        }
        try {
            ObjectMapper om = new ObjectMapper();
            return (Map<String, String>) om.readValue(f, Map.class);
        } catch (IOException e) {
            throw new RuntimeException("Failed to load sql.json", e);
        }
    }

    public static String getQuery(String key) {
        String query = queries.get(key);
        if (query == null) {
            throw new IllegalArgumentException("No SQL query found for key: " + key);
        }
        return query;
    }
}
