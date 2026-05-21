package utils;

import config.ConfigManager;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class EncryptUtil {

    public static String encrypt(String plainText, String key) throws Exception {
        if (key.length() != 16) {
            throw new IllegalArgumentException("AES key must be 16 characters");
        }

        Cipher cipher = Cipher.getInstance("AES");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(), "AES");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        byte[] encrypted = cipher.doFinal(plainText.getBytes());

        return Base64.getEncoder().encodeToString(encrypted);
    }

    public static String encryptWithConfigKey(String plainText) throws Exception {
        String key = ConfigManager.getProperty("aes.key");
        if (key == null || key.length() != 16) {
            throw new IllegalArgumentException("aes.key must be set and 16 characters long in config.properties");
        }
        return encrypt(plainText, key);
    }
}
