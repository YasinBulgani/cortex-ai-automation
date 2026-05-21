/**
 * Kullanıcıya gösterilecek hata metinlerini Türkçe'ye ve dosta çevirir.
 *
 * Backend bazen İngilizce FastAPI default'ları (`Not Found`, `Forbidden`,
 * validation hataları) döndürür; ham stacktrace ise korkutucudur.
 * Bu modül teknik mesajı saklar, kullanıcıya anlamlı özet verir.
 */

export interface FriendlyError {
  title: string;
  message: string;
  /** İsteğe bağlı: detay (copy-to-clipboard ile gösterilebilir) */
  detail?: string;
  /** İsteğe bağlı: 4xx/5xx kodu */
  status?: number;
}

const STATUS_MAP: Record<number, string> = {
  400: "Gönderilen istek geçerli değil.",
  401: "Oturumunuz düşmüş olabilir, lütfen yeniden giriş yapın.",
  403: "Bu işlem için yetkiniz yok.",
  404: "Aradığınız kayıt bulunamadı.",
  408: "İstek zaman aşımına uğradı.",
  409: "Başka bir işlemle çakıştı, lütfen tekrar deneyin.",
  413: "Yüklediğiniz dosya çok büyük.",
  422: "Bazı alanlar eksik veya geçersiz.",
  429: "Çok fazla istek — lütfen bir süre bekleyin.",
  500: "Sunucuda bir hata oluştu. Ekibimiz bilgilendirildi.",
  502: "Arka servise ulaşılamıyor.",
  503: "Servis şu an müsait değil.",
  504: "Sunucu yanıt vermedi (zaman aşımı).",
};

const KEYWORD_MAP: Array<[RegExp, string]> = [
  [/network|failed to fetch|load failed/i, "Ağ bağlantısı kesilmiş olabilir."],
  [/timeout|timed?\s?out/i, "İstek zaman aşımına uğradı."],
  [/cors/i, "Güvenlik politikası nedeniyle istek engellendi."],
  [/not\s?found/i, "Kayıt bulunamadı."],
  [/unauthor(ized|ised)|invalid token|expired/i, "Oturum doğrulanamadı."],
  [/forbidden/i, "Yetkisiz erişim."],
];

/**
 * Verilen hatayı kullanıcıya gösterilecek Türkçe mesaja çevirir.
 * Orijinal hata `detail` alanında "Detayları göster" için saklanır.
 */
export function friendlyError(err: unknown): FriendlyError {
  if (err == null) {
    return { title: "Bilinmeyen hata", message: "Beklenmeyen bir durum oluştu." };
  }

  // Error tipinde ise message + status arıyoruz
  const raw =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : JSON.stringify(err).slice(0, 500);

  // Status kodu varsa yakala (ör. "403 Forbidden", "{status:404}")
  const statusMatch = raw.match(/\b([4-5]\d{2})\b/);
  const status = statusMatch ? Number(statusMatch[1]) : undefined;

  let message: string | undefined;
  if (status && STATUS_MAP[status]) {
    message = STATUS_MAP[status];
  } else {
    for (const [pattern, msg] of KEYWORD_MAP) {
      if (pattern.test(raw)) {
        message = msg;
        break;
      }
    }
  }

  if (!message) {
    message = "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.";
  }

  return {
    title: status ? `Hata ${status}` : "Bir hata oluştu",
    message,
    detail: raw,
    status,
  };
}

/** Tarayıcının panoya kopyalama desteği varsa metni kopyalar, başarıyı döner. */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.clipboard) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
