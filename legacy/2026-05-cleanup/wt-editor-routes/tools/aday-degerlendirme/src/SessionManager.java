import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

public class SessionManager {
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss");

    private final Path dataDir;

    public SessionManager(Path dataDir) {
        this.dataDir = dataDir;
    }

    public Session createSession(String candidateName) throws IOException {
        Files.createDirectories(dataDir);

        String slug = slugify(candidateName);
        String ts = LocalDateTime.now(ZoneId.systemDefault()).format(TS);
        Path baseDir = dataDir.resolve(ts + "_" + slug);
        Path audioDir = baseDir.resolve("audio");

        Files.createDirectories(audioDir);

        Path notes = baseDir.resolve("notes.md");
        Path sessionJson = baseDir.resolve("session.json");
        Path audioFile = audioDir.resolve("mic.wav");

        Instant now = Instant.now();

        if (!Files.exists(notes)) {
            Files.writeString(
                    notes,
                    "# Görüşme Notları\n\n- Aday: " + candidateName + "\n- Başlangıç: " + now + "\n",
                    StandardCharsets.UTF_8
            );
        }

        Session session = new Session(
                candidateName,
                slug,
                now,
                baseDir,
                audioDir,
                audioFile,
                sessionJson,
                notes
        );

        writeSessionJson(session);
        return session;
    }

    private static void writeSessionJson(Session session) throws IOException {
        String json = "{\n"
                + "  \"candidateName\": " + jsonString(session.candidateName()) + ",\n"
                + "  \"slug\": " + jsonString(session.slug()) + ",\n"
                + "  \"startedAt\": " + jsonString(session.startedAt().toString()) + ",\n"
                + "  \"baseDir\": " + jsonString(session.baseDir().toString()) + ",\n"
                + "  \"audioFile\": " + jsonString(session.audioFile().toString()) + "\n"
                + "}\n";
        Files.writeString(session.sessionJson(), json, StandardCharsets.UTF_8);
    }

    private static String jsonString(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private static String slugify(String input) {
        String s = input == null ? "" : input.trim().toLowerCase();
        s = s.replaceAll("[^\\p{IsAlphabetic}\\p{IsDigit}]+", "-");
        s = s.replaceAll("^-+|-+$", "");
        if (s.isBlank()) return "aday";
        return s;
    }
}

