package utils;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import crypto.PasswordManager;
import config.ConfigManager;

/**
 * AES decryption — backward-compatible iki mod:
 * <ul>
 *   <li>v2 (GCM): {@code v2:} prefix'li girdiler. IV ilk 12 byte'tir.</li>
 *   <li>v1 (ECB, deprecated): prefix yoksa eski yolla decode eder. Sadece eski
 *       password.properties girdileri icin korunmustur.</li>
 * </ul>
 */
public class DecryptUtil {

    private static final int GCM_IV_BYTES = 12;
    private static final int GCM_TAG_BITS = 128;

    /** Otomatik mod secimi: v2: prefix'i varsa GCM, yoksa eski ECB. */
    public static String decrypt(String encryptedData, String key) throws Exception {
        if (key == null || key.length() != 16) {
            throw new IllegalArgumentException("AES key must be exactly 16 characters");
        }
        if (encryptedData != null && encryptedData.startsWith(EncryptUtil.V2_PREFIX)) {
            return decryptGcm(encryptedData.substring(EncryptUtil.V2_PREFIX.length()), key);
        }
        return decryptEcb(encryptedData, key);
    }

    private static String decryptGcm(String base64Body, String key) throws Exception {
        byte[] raw = Base64.getDecoder().decode(base64Body);
        if (raw.length <= GCM_IV_BYTES) {
            throw new IllegalArgumentException("v2 ciphertext too short (missing IV)");
        }
        byte[] iv = new byte[GCM_IV_BYTES];
        System.arraycopy(raw, 0, iv, 0, GCM_IV_BYTES);
        byte[] ciphertext = new byte[raw.length - GCM_IV_BYTES];
        System.arraycopy(raw, GCM_IV_BYTES, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "AES");
        cipher.init(Cipher.DECRYPT_MODE, keySpec, new GCMParameterSpec(GCM_TAG_BITS, iv));
        return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
    }

    /**
     * @deprecated Eski ECB sifrelenmis veriler icin. Yeni v2 (GCM) cikislari
     * uretmek icin {@link EncryptUtil#encryptGcm(String, String)} kullanin.
     */
    @Deprecated
    private static String decryptEcb(String encryptedData, String key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "AES");
        cipher.init(Cipher.DECRYPT_MODE, keySpec);
        byte[] decodedBytes = Base64.getDecoder().decode(encryptedData);
        byte[] decryptedBytes = cipher.doFinal(decodedBytes);
        return new String(decryptedBytes, StandardCharsets.UTF_8);
    }

    public static String decryptPasswordByAlias(String alias) throws Exception {
        String encrypted = PasswordManager.getPassword(alias);
        if (encrypted == null) {
            throw new IllegalArgumentException(
                "No encrypted password found for alias: \"" + alias + "\".\n" +
                "Fix options:\n" +
                "  1. Re-record the scenario — the Cortex Recorder auto-encrypts\n" +
                "     typed passwords and saves them under the correct alias.\n" +
                "  2. Encrypt manually:\n" +
                "       a) Set CORTEX_AES_KEY=<your-16-char-key> in .env\n" +
                "       b) Call EncryptionManager.encryptAndSaveToPasswordFile(<plain>, \"" + alias + "\")\n" +
                "  Known aliases in password.properties: " + PasswordManager.listAliases()
            );
        }

        String key = ConfigManager.getProperty("aes.key");
        if (key == null || key.isBlank()) {
            throw new IllegalStateException(
                "AES key missing — cannot decrypt alias \"" + alias + "\".\n" +
                "Fix: copy .env.example to .env and set CORTEX_AES_KEY=<16 chars>."
            );
        }
        if (key.length() != 16) {
            throw new IllegalArgumentException(
                "CORTEX_AES_KEY must be exactly 16 characters (current: "
                + key.length() + "). Fix: update CORTEX_AES_KEY in .env."
            );
        }
        try {
            return decrypt(encrypted, key);
        } catch (Exception e) {
            throw new RuntimeException(
                "Decryption failed for alias \"" + alias + "\": " + e.getMessage() + "\n" +
                "Likely cause: the value in password.properties was encrypted with a different\n" +
                "CORTEX_AES_KEY than the one currently set in .env.\n" +
                "Fix: re-run EncryptionManager.encryptAndSaveToPasswordFile(<plain>, \"" + alias + "\")" +
                " with the current key.",
                e
            );
        }
    }
}
