import { friendlyError, copyToClipboard } from "../errors";

describe("friendlyError", () => {
  describe("null / undefined", () => {
    it("null → bilinmeyen hata", () => {
      const r = friendlyError(null);
      expect(r.title).toBe("Bilinmeyen hata");
      expect(r.message).toContain("Beklenmeyen");
    });

    it("undefined → bilinmeyen hata", () => {
      expect(friendlyError(undefined).title).toBe("Bilinmeyen hata");
    });
  });

  describe("HTTP durum kodları", () => {
    it.each([
      [400, "Gönderilen istek geçerli değil."],
      [401, "Oturumunuz düşmüş olabilir, lütfen yeniden giriş yapın."],
      [403, "Bu işlem için yetkiniz yok."],
      [404, "Aradığınız kayıt bulunamadı."],
      [422, "Bazı alanlar eksik veya geçersiz."],
      [429, "Çok fazla istek — lütfen bir süre bekleyin."],
      [500, "Sunucuda bir hata oluştu. Ekibimiz bilgilendirildi."],
      [503, "Servis şu an müsait değil."],
    ])("%i kodu → doğru Türkçe mesaj", (status, expected) => {
      const err = new Error(`${status} error`);
      const r = friendlyError(err);
      expect(r.message).toBe(expected);
      expect(r.status).toBe(status);
    });

    it("başlık 'Hata <kod>' formatında", () => {
      const r = friendlyError(new Error("404 Not Found"));
      expect(r.title).toBe("Hata 404");
    });
  });

  describe("anahtar kelime eşleştirme", () => {
    it.each([
      ["network error", "Ağ bağlantısı"],
      ["Failed to fetch", "Ağ bağlantısı"],
      ["request timed out", "zaman aşımına"],
      ["CORS policy", "Güvenlik politikası"],
      ["Not found", "bulunamadı"],
      ["Unauthorized access", "Oturum doğrulanamadı"],
      ["expired token", "Oturum doğrulanamadı"],
      ["Forbidden", "Yetkisiz erişim"],
    ])('"%s" → "%s" içerir', (input, expected) => {
      const r = friendlyError(new Error(input));
      expect(r.message).toContain(expected);
    });
  });

  describe("ham metin ve JSON", () => {
    it("string hata kabul edilir", () => {
      const r = friendlyError("Beklenmeyen hata oluştu");
      expect(r.title).toBe("Bir hata oluştu");
    });

    it("obje JSON olarak serileştirilir, detail'de görünür", () => {
      const r = friendlyError({ code: "UNKNOWN" });
      expect(r.detail).toContain("UNKNOWN");
    });

    it("tanınmayan hata → fallback mesajı", () => {
      const r = friendlyError(new Error("xyz completely unknown error abc"));
      expect(r.message).toContain("Beklenmeyen");
    });
  });

  describe("detail alanı", () => {
    it("Error.message değeri detail'e aktarılır", () => {
      const r = friendlyError(new Error("Stack trace here"));
      expect(r.detail).toContain("Stack trace here");
    });
  });
});

describe("copyToClipboard", () => {
  it("navigator.clipboard mevcut değilse false döner", async () => {
    const original = navigator.clipboard;
    Object.defineProperty(navigator, "clipboard", { value: undefined, writable: true });
    const result = await copyToClipboard("test");
    expect(result).toBe(false);
    Object.defineProperty(navigator, "clipboard", { value: original, writable: true });
  });

  it("writeText başarılıysa true döner", async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
    });
    const result = await copyToClipboard("merhaba");
    expect(result).toBe(true);
    expect(writeText).toHaveBeenCalledWith("merhaba");
  });

  it("writeText atarsa false döner", async () => {
    const writeText = jest.fn().mockRejectedValue(new Error("izin yok"));
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
    });
    const result = await copyToClipboard("test");
    expect(result).toBe(false);
  });
});
