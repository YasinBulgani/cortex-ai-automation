import java.nio.file.Path;
import java.time.Instant;

public record Session(
        String candidateName,
        String slug,
        Instant startedAt,
        Path baseDir,
        Path audioDir,
        Path audioFile,
        Path sessionJson,
        Path notesFile
) {
}

