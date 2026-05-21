import java.nio.file.Path;
import java.time.Instant;

public record AudioRecording(
        Path audioFile,
        Instant startedAt,
        Process process
) {
}

