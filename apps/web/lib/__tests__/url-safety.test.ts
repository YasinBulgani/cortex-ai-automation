import { getSafeNextPath } from "../api-client";

describe("getSafeNextPath — açık yönlendirme önleme (production kodu)", () => {
  describe("güvenli yollar — olduğu gibi döner", () => {
    it.each([
      "/projects",
      "/p/proj-1/scenarios",
      "/p/proj-1?tab=2",
      "/p/proj-1#section",
      "/scenarios?filter=active",
      "/approvals",
    ])('"%s" güvenli yol olarak geçer', (path) => {
      expect(getSafeNextPath(path)).toBe(path);
    });
  });

  describe("engellenen girişler — boş string döner", () => {
    it("null için boş döner", () => {
      expect(getSafeNextPath(null)).toBe("");
    });

    it("boş string için boş döner", () => {
      expect(getSafeNextPath("")).toBe("");
    });

    it("/login kendi sayfasını reddeder", () => {
      expect(getSafeNextPath("/login")).toBe("");
    });

    it("/login alt yolunu reddeder", () => {
      expect(getSafeNextPath("/login/callback")).toBe("");
    });

    it("protokol-göreli URL reddedilir (//evil.com)", () => {
      expect(getSafeNextPath("//evil.com")).toBe("");
    });

    it("mutlak URL reddedilir (/ ile başlamıyor)", () => {
      expect(getSafeNextPath("relative/path")).toBe("");
    });

    it("yalnızca boşluk reddedilir", () => {
      expect(getSafeNextPath("   ")).toBe("");
    });
  });

  describe("header injection saldırıları", () => {
    it("ters eğik çizgi enjeksiyonu reddedilir", () => {
      expect(getSafeNextPath("/path\\evil")).toBe("");
    });

    it("newline enjeksiyonu reddedilir", () => {
      expect(getSafeNextPath("/path\nHeader: injected")).toBe("");
    });

    it("carriage return enjeksiyonu reddedilir", () => {
      expect(getSafeNextPath("/path\rHeader: injected")).toBe("");
    });
  });
});
