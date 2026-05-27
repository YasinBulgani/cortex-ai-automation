package crypto;

import config.ConfigManager;
import utils.EncryptUtil;

public class EncryptionManager {

    public static void encryptAndSaveToPasswordFile(String plainPassword, String alias) {
        try {
            String aesKey = ConfigManager.getProperty("aes.key");
            if (aesKey == null || aesKey.isBlank()) {
                throw new IllegalStateException(
                    "AES key missing. Copy .env.example to .env and set " +
                    "CORTEX_AES_KEY=<16 chars>."
                );
            }
            if (aesKey.length() != 16) {
                throw new IllegalArgumentException(
                    "CORTEX_AES_KEY must be exactly 16 characters (current: " + aesKey.length() + ")"
                );
            }

            // Yeni sifrelemeler v2 (AES/GCM) — DecryptUtil prefix'e bakarak otomatik mod secer.
            String encryptedPassword = EncryptUtil.encryptGcm(plainPassword, aesKey);

            PasswordManager.setPassword(alias, encryptedPassword);
            PasswordManager.save();

            System.out.println("Encrypted password saved to password.properties as alias: " + alias);

        } catch (Exception e) {
            throw new RuntimeException("Failed to encrypt and save password", e);
        }
    }
}
