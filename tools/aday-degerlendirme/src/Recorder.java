import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;

public interface Recorder {
    AudioRecording start(Session session) throws Exception;

    void stop(AudioRecording recording) throws Exception;

    static Recorder autoDetect() {
        if (FfmpegRecorder.isFfmpegAvailable()) {
            return new FfmpegRecorder();
        }
        return new NoopRecorder();
    }

    final class NoopRecorder implements Recorder {
        @Override
        public AudioRecording start(Session session) {
            return null;
        }

        @Override
        public void stop(AudioRecording recording) {
            // no-op
        }
    }
}

