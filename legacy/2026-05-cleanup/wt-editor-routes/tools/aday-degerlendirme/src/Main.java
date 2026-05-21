import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Path;

public class Main {
    public static void main(String[] args) throws Exception {
        if (args.length == 0 || "help".equalsIgnoreCase(args[0]) || "--help".equalsIgnoreCase(args[0])) {
            printHelp();
            return;
        }

        String cmd = args[0].toLowerCase();
        if ("start".equals(cmd)) {
            if (args.length < 2) {
                System.err.println("Eksik parametre: aday adı. Örn: start \"Ada Lovelace\"");
                System.exit(2);
            }

            String candidateName = args[1];
            SessionManager manager = new SessionManager(Path.of("data"));
            Session session = manager.createSession(candidateName);

            System.out.println("Oturum klasörü: " + session.baseDir());
            System.out.println("Notlar: " + session.notesFile());

            Recorder recorder = Recorder.autoDetect();
            AudioRecording recording = null;
            try {
                recording = recorder.start(session);
                if (recording != null) {
                    System.out.println("Kayıt başladı: " + recording.audioFile());
                } else {
                    System.out.println("Kayıt başlatılamadı (ffmpeg yok gibi). README.md içindeki kurulum adımlarını uygula.");
                }

                System.out.println("Görüşme bitince Enter'a bas: ");
                new BufferedReader(new InputStreamReader(System.in)).readLine();
            } finally {
                if (recording != null) {
                    recorder.stop(recording);
                    System.out.println("Kayıt durduruldu.");
                }
                // Görüşme bittikten sonra, varsa LLM ile özet al
                LlmClient llm = LlmClient.fromEnvOrNull();
                if (llm != null) {
                    System.out.println("LLM'den değerlendirme isteniyor...");
                    try {
                        String summary = llm.summarizeSession(session);
                        System.out.println("LLM özeti:");
                        System.out.println(summary);
                    } catch (Exception e) {
                        System.err.println("LLM çağrısı başarısız: " + e.getMessage());
                    }
                } else {
                    System.out.println("LLM entegrasyonu için OPENAI_API_KEY ortam değişkenini ayarla (detay için README.md).");
                }
            }
            return;
        }

        System.err.println("Bilinmeyen komut: " + cmd);
        printHelp();
        System.exit(2);
    }

    private static void printHelp() {
        System.out.println("Kullanım:");
        System.out.println("  java -cp src Main start \"Aday Adı\"");
        System.out.println();
        System.out.println("Not: Ses kaydı için ffmpeg önerilir. Kurulum: README.md");
    }
}
