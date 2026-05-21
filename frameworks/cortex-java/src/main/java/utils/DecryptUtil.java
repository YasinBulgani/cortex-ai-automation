package utils;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;
import crypto.PasswordManager;
import config.ConfigManager;

public class DecryptUtil {

    public static String decrypt(String encryptedData, String key) throws Exception {
        if (key.length() != 16) {
            throw new IllegalArgumentException("AES key must be exactly 16 characters");
        }

        Cipher cipher = Cipher.getInstance("AES");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(), "AES");
        cipher.init(Cipher.DECRYPT_MODE, keySpec);

        byte[] decodedBytes = Base64.getDecoder().decode(encryptedData);
        byte[] decryptedBytes = cipher.doFinal(decodedBytes);

        return new String(decryptedBytes);
    }

    public static String decryptPasswordByAlias(String alias) throws Exception {
        String encrypted = PasswordManager.getPassword(alias);
        if (encrypted == null) {
            throw new IllegalArgumentException("No encrypted password found for alias: " + alias);
        }

        String key = ConfigManager.getProperty("aes.key");
        if (key == null || key.isBlank()) {
            throw new IllegalStateException(
                "AES key missing. Copy .env.example to .env and set " +
                "CORTEX_AES_KEY=<16 chars>."
            );
        }
        if (key.length() != 16) {
            throw new IllegalArgumentException(
                "CORTEX_AES_KEY must be exactly 16 characters (current: " + key.length() + ")"
            );
        }
        return decrypt(encrypted, key);
    }
}
