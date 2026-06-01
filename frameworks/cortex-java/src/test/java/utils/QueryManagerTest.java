package utils;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for QueryManager — the classpath-based SQL query registry.
 *
 * Relies on {@code sqlQueries/sql.json} being available on the test classpath
 * (it lives in {@code src/main/resources/}, which Maven includes in tests).
 */
class QueryManagerTest {

    @Test
    void get_known_query_returns_non_null_string() {
        String sql = QueryManager.getQuery("selectUserByEmail");
        assertNotNull(sql, "Known query key must return a SQL string");
        assertFalse(sql.isBlank(), "SQL string must not be blank");
    }

    @Test
    void get_unknown_key_throws_illegal_argument_exception() {
        IllegalArgumentException ex = assertThrows(
                IllegalArgumentException.class,
                () -> QueryManager.getQuery("nonExistentKey_xyzzy"));
        assertTrue(ex.getMessage().contains("nonExistentKey_xyzzy"),
                "Exception message should mention the offending key");
    }

    @Test
    void get_null_key_throws_exception() {
        // null is not registered — should throw (HashMap.get(null) returns null → exception path)
        assertThrows(Exception.class,
                () -> QueryManager.getQuery(null),
                "null key should throw either IllegalArgumentException or NullPointerException");
    }

    @Test
    void known_query_contains_expected_sql_keywords() {
        String sql = QueryManager.getQuery("selectUserByEmail");
        assertTrue(sql.toUpperCase().contains("SELECT"),
                "selectUserByEmail should be a SELECT statement");
        assertTrue(sql.contains("?"),
                "SQL should contain at least one JDBC placeholder '?'");
    }

    @Test
    void second_known_query_is_accessible() {
        String sql = QueryManager.getQuery("selectUserById");
        assertNotNull(sql);
        assertTrue(sql.toUpperCase().contains("SELECT"));
        assertTrue(sql.contains("?"));
    }
}
