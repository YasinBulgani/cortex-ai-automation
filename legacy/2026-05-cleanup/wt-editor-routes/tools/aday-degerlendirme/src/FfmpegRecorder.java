import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class FfmpegRecorder implements Recorder {

    /**
     * macOS (avfoundation) varsayılan audio device seçimi.
     * Örn: ":0" (video yok, audio device index 0)
     */
    private static final String DEFAULT_AVFOUNDATION_DEVICE = ":0";

    public static boolean isFfmpegAvailable() {
        try {
            Process p = new ProcessBuilder("ffmpeg", "-version")
                    .redirectErrorStream(true)
                    .start();
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    public AudioRecording start(Session session) throws Exception {
        // ffmpeg yoksa hiç başlamayalım
        if (!isFfmpegAvailable()) return null;

        String device = System.getenv().getOrDefault("AUDIO_DEVICE", DEFAULT_AVFOUNDATION_DEVICE);

        List<String> cmd = new ArrayList<>();
        cmd.add("ffmpeg");
        cmd.add("-hide_banner");
        cmd.add("-loglevel");
        cmd.add("warning");
        cmd.add("-y");
        cmd.add("-f");
        cmd.add("avfoundation");
        cmd.add("-i");
        cmd.add(device);
        cmd.add("-ac");
        cmd.add("1");
        cmd.add("-ar");
        cmd.add("48000");
        cmd.add(session.audioFile().toString());

        Process process = new ProcessBuilder(cmd)
                .redirectErrorStream(true)
                .start();

        return new AudioRecording(session.audioFile(), Instant.now(), process);
    }

    @Override
    public void stop(AudioRecording recording) throws Exception {
        Process p = recording.process();
        if (!p.isAlive()) return;

        // ffmpeg'e "q" yazarak nazikçe durdurmayı dene
        try {
            BufferedWriter w = new BufferedWriter(new OutputStreamWriter(p.getOutputStream(), StandardCharsets.UTF_8));
            w.write("q\n");
            w.flush();
        } catch (IOException ignored) {
            // bazı durumlarda stdin kapalı olabilir
        }

        boolean exited = p.waitFor(3, java.util.concurrent.TimeUnit.SECONDS);
        if (!exited && p.isAlive()) {
            p.destroy();
            p.waitFor(2, java.util.concurrent.TimeUnit.SECONDS);
        }
        if (p.isAlive()) {
            p.destroyForcibly();
            p.waitFor();
        }
    }
}

