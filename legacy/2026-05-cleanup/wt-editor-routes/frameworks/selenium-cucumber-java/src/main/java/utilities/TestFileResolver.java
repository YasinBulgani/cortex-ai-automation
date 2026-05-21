package utilities;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * Proje içindeki testFile klasöründen (src/test/resources/testFile) uzantıya göre dosya yolu döndürür.
 * Örnek: "pdf" → testFile içindeki .pdf uzantılı dosya; "Doc" → .doc uzantılı dosya (büyük/küçük harf duyarsız).
 */
public final class TestFileResolver {

    /** src/test/resources/testFile — test dosyaları bu klasörde olmalı */
    private static final Path TEST_FILE_FOLDER = Paths.get("src", "test", "resources", "testFile");

    private TestFileResolver() {
    }

    /**
     * Verilen değeri dosya yolu olarak çözümler:
     * <ul>
     *   <li>Tam yol içeriyorsa (örn. "C:/dokuman.pdf") aynen döner.</li>
     *   <li>Sadece uzantı ise (örn. "pdf", "Doc", "docx") testFile klasöründe
     *       o uzantıya sahip ilk dosyanın tam yolunu döner (uzantı eşlemesi büyük/küçük harf duyarsız).</li>
     * </ul>
     *
     * @param fileSpec Dosya uzantısı (pdf, Doc, docx vb.) veya tam dosya yolu
     * @return Kullanılacak dosyanın mutlak yolu
     * @throws RuntimeException testFile klasörü yoksa veya ilgili uzantıda dosya bulunamazsa
     */
    public static String getFilePath(String fileSpec) {
        if (fileSpec == null || fileSpec.isBlank()) {
            throw new RuntimeException("Dosya belirtilmedi (boş veya null).");
        }
        String trimmed = fileSpec.trim();

        // Tam yol: path separator veya Windows sürücü (C:) varsa olduğu gibi kullan
        if (trimmed.contains("/") || trimmed.contains("\\") || isWindowsAbsolutePath(trimmed)) {
            Path path = Paths.get(trimmed);
            if (!Files.exists(path)) {
                throw new RuntimeException("Belirtilen dosya bulunamadı: " + trimmed);
            }
            return path.toAbsolutePath().toString();
        }

        // Uzantı olarak kabul et: nokta varsa "docx" gibi, yoksa "pdf" -> .pdf
        String extension = trimmed.startsWith(".") ? trimmed : "." + trimmed;

        Path testFileDir = TEST_FILE_FOLDER.toAbsolutePath().normalize();
        if (!Files.isDirectory(testFileDir)) {
            throw new RuntimeException(
                    "testFile klasörü bulunamadı. 'src/test/resources/testFile' altında olmalı. Aranan: "
                            + testFileDir);
        }

        try (Stream<Path> list = Files.list(testFileDir)) {
            Optional<Path> found = list
                    .filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().toLowerCase().endsWith(extension.toLowerCase()))
                    .findFirst();

            if (found.isEmpty()) {
                throw new RuntimeException(
                        "testFile klasöründe '" + extension + "' uzantılı dosya bulunamadı. Klasör: " + testFileDir);
            }
            return found.get().toAbsolutePath().toString();
        } catch (IOException e) {
            throw new RuntimeException("testFile klasörü okunamadı: " + testFileDir, e);
        }
    }

    private static boolean isWindowsAbsolutePath(String s) {
        return s.length() >= 2 && Character.isLetter(s.charAt(0)) && s.charAt(1) == ':';
    }
}
