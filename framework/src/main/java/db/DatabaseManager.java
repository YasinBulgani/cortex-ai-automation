package db;

import config.ConfigManager;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

public class DatabaseManager {
    private static final Map<String, Connection> connections = new HashMap<>();

    /**
     * Belirtilen veritabanı kimliği için bağlantıyı oluşturur veya mevcut bağlantıyı döndürür.
     *
     * @param dbIdentifier Veritabanı kimliği (örn: "db1").
     * @return Connection Veritabanı bağlantısı.
     * @throws SQLException Bağlantı sırasında hata oluşursa fırlatılır.
     */
    public static Connection getConnection(String dbIdentifier) throws SQLException {
        if (!connections.containsKey(dbIdentifier)) {
            String url = ConfigManager.getProperty(dbIdentifier + ".url");
            String username = ConfigManager.getProperty(dbIdentifier + ".username");
            String password = ConfigManager.getProperty(dbIdentifier + ".password");

            if (url == null || username == null || password == null) {
                throw new IllegalArgumentException("Missing configuration for database: " + dbIdentifier);
            }

            Connection connection = DriverManager.getConnection(url, username, password);
            connections.put(dbIdentifier, connection);
        }
        return connections.get(dbIdentifier);
    }

    /**
     * Veritabanı bağlantısını kapatır.
     *
     * @param dbIdentifier Veritabanı kimliği (örn: "db1").
     */
    public static void closeConnection(String dbIdentifier) {
        try {
            Connection connection = connections.get(dbIdentifier);
            if (connection != null && !connection.isClosed()) {
                connection.close();
                connections.remove(dbIdentifier);
                System.out.println("Connection to " + dbIdentifier + " closed.");
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to close connection for: " + dbIdentifier, e);
        }
    }

    /**
     * Tüm veritabanı bağlantılarını kapatır.
     */
    public static void closeAllConnections() {
        for (String dbIdentifier : connections.keySet()) {
            closeConnection(dbIdentifier);
        }
    }
}
