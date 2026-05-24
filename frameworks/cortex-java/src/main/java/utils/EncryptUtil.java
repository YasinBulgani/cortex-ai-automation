package utils;

import config.ConfigManager;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * AES sifreleme yardimcisi.
 *
 * <p><b>Iki mod desteklenir:</b></p>
 * <ul>
 *   <li><b>v2 (varsayilan)</b> — {@link #encryptGcm(String, String)}: AES/GCM/NoPadding,
 *       12-byte rastgele IV, authenticated encryption. Cikti formati:
 *       {@code v2:<base64(IV || ciphertext || tag)>}.</li>
 *   <li><b>v1 (deprecated)</b> — {@link #encrypt(String, String)}: AES/ECB (Java default).
 *       Pattern-leak ve mut'tested-padding zafiyetleri var; SADECE eski password.properties
 *       girdileriyle geri uyumluluk icin korunuyor. Yeni sifrelemeler v2 kullanmali.</li>
 * </ul>
 *
 * <p>Decryption tarafi (DecryptUtil) {@code v2:} prefix'ine bakarak otomatik mod secer.</p>
 */
public class EncryptUtil {

    /** v2 (GCM) ciktilarinin Base64 govdesinin onunde tasidigi prefix. */
    static final String V2_PREFIX = "v2:";
    private static final int GCM_IV_BYTES = 12;
    private static final int GCM_TAG_BITS = 128;
    private static final SecureRandom RNG = new SecureRandom();

    /**
     * Yeni — AES/GCM/NoPadding ile sifreler. IV her cagrida rastgele.
     * Cikti: {@code v2:<base64>}.
     */
    public static String encryptGcm(String plainText, String key) throws Exception {
        if (key == null || key.length() != 16) {
            throw new IllegalArgumentException("AES key must be exactly 16 characters");
        }
        byte[] iv = new byte[GCM_IV_BYTES];
        RNG.nextBytes(iv);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "AES");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, new GCMParameterSpec(GCM_TAG_BITS, iv));

        byte[] ciphertext = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
        byte[] out = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, out, 0, iv.length);
        System.arraycopy(ciphertext, 0, out, iv.length, ciphertext.length);

        return V2_PREFIX + Base64.getEncoder().encodeToString(out);
    }

    /**
     * @deprecated AES/ECB kullanir — pattern-leak ve padding zafiyetleri vardir.
     * Yeni sifrelemelerde {@link #encryptGcm(String, String)} kullanin. Bu metod yalnizca
     * eski password.properties girdilerini regenerate ederken sifreyi bozmamak icin durur.
     */
    @Deprecated
    public static String encrypt(String plainText, String key) throws Exception {
        if (key == null || key.length() != 16) {
            throw new IllegalArgumentException("AES key must be 16 characters");
        }
        Cipher cipher = Cipher.getInstance("AES");
        SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "AES");
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        byte[] encrypted = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(encrypted);
    }

    /** Config'den aes.key okuyup GCM ile sifreler. */
    public static String encryptWithConfigKey(String plainText) throws Exception {
        String key = ConfigManager.getProperty("aes.key");
        if (key == null || key.length() != 16) {
            throw new IllegalArgumentException("aes.key must be set and 16 characters long in config.properties");
        }
        return encryptGcm(plainText, key);
    }
}
