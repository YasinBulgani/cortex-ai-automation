package playwright.methods;

import config.ConfigManager;
import crypto.PasswordManager;
import utils.DecryptUtil;
import utils.QueryManager;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;

/**
 * Thread-safe database operations for Playwright step defs.
 *
 * Each scenario thread owns its own connection. The connection is stored in
 * a ThreadLocal so the same instance can be re-used inside a single scenario
 * (connect -> execute -> close).
 */
public class PwDbMethods {

    private static final ThreadLocal<Connection> CONN = new ThreadLocal<>();

    public void connectToDatabase(String url, String username, String password) {
        try {
            Connection c = DriverManager.getConnection(url, username, password);
            CONN.set(c);
            System.out.println("[PwDbMethods] Connected to database");
        } catch (SQLException e) {
            throw new RuntimeException("Failed to connect to the database", e);
        }
    }

    /** Connect using a config identifier (db1, db2, ...) + the encrypted password store. */
    public void connectToDatabaseByIdentifier(String dbIdentifier) {
        String url = ConfigManager.getProperty(dbIdentifier + ".url");
        String username = ConfigManager.getProperty(dbIdentifier + ".username");
        String encryptedPassword = PasswordManager.getPassword(dbIdentifier.trim());

        if (url == null || username == null || encryptedPassword == null) {
            throw new IllegalArgumentException(
                "Missing config for db identifier '" + dbIdentifier + "': "
                    + (url == null ? "[url] " : "")
                    + (username == null ? "[username] " : "")
                    + (encryptedPassword == null ? "[encrypted.password] " : "")
            );
        }

        try {
            String aesKey = ConfigManager.getProperty("aes.key");
            String password = DecryptUtil.decrypt(encryptedPassword, aesKey);
            connectToDatabase(url, username, password);
            System.out.println("[PwDbMethods] Connected with identifier: " + dbIdentifier);
        } catch (Exception e) {
            throw new RuntimeException("Failed to connect to DB with identifier: " + dbIdentifier, e);
        }
    }

    /** Execute a parameterized SQL statement looked up by key in sqlQueries/sql.json. */
    public void executeSqlFromJson(String queryKey, String parameters) {
        Connection c = CONN.get();
        if (c == null) {
            throw new IllegalStateException("Database connection is not established");
        }
        String sql = QueryManager.getQuery(queryKey);
        if (sql == null) {
            throw new IllegalArgumentException("No SQL query found for key: " + queryKey);
        }
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            String[] params = parameters == null || parameters.isBlank()
                    ? new String[0]
                    : parameters.split(",");
            for (int i = 0; i < params.length; i++) {
                ps.setObject(i + 1, params[i].trim());
            }
            ps.execute();
            System.out.println("[PwDbMethods] Executed SQL: " + queryKey);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to execute SQL: " + queryKey, e);
        }
    }

    public void closeConnection() {
        Connection c = CONN.get();
        if (c == null) return;
        try {
            if (!c.isClosed()) c.close();
            System.out.println("[PwDbMethods] Connection closed");
        } catch (SQLException e) {
            throw new RuntimeException("Error closing database connection", e);
        } finally {
            CONN.remove();
        }
    }

    public Connection getConnection() {
        return CONN.get();
    }
}
