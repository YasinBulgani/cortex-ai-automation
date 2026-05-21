package crypto;

import java.io.*;
import java.util.Properties;

public class PasswordManager {
    private static final Properties properties = new Properties();
    private static final String PASSWORD_PATH = "src/main/resources/password.properties";

    static {
        try (FileInputStream fis = new FileInputStream(PASSWORD_PATH)) {
            properties.load(fis);
        } catch (IOException e) {
            System.err.println("❌ Failed to load password.properties");
            e.printStackTrace();
            throw new RuntimeException(e);
        }
    }

    public static String getPassword(String alias) {
        return properties.getProperty("encrypted.password." + alias);
    }

    public static void setPassword(String alias, String encryptedValue) {
        properties.setProperty("encrypted.password." + alias, encryptedValue);
    }

    public static boolean contains(String alias) {
        return properties.containsKey("encrypted.password." + alias);
    }

    public static void save() {
        try (FileOutputStream output = new FileOutputStream(PASSWORD_PATH)) {
            properties.store(output, null);
        } catch (IOException e) {
            throw new RuntimeException("❌ Failed to save password.properties", e);
        }
    }

    public static String getRaw(String key) {
        return properties.getProperty(key);
    }

}

