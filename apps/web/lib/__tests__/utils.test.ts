import { cn } from "../utils";

describe("cn — tailwind sınıf birleştirici", () => {
  it("tek sınıf döndürür", () => {
    expect(cn("text-red-500")).toBe("text-red-500");
  });

  it("birden fazla sınıfı birleştirir", () => {
    expect(cn("flex", "items-center", "gap-2")).toBe("flex items-center gap-2");
  });

  it("çakışan tailwind sınıflarını birleştirir — son kazanır", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
    expect(cn("p-4", "p-8")).toBe("p-8");
  });

  it("koşullu sınıfları clsx ile değerlendirir", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
    expect(cn("base", true && "active")).toBe("base active");
  });

  it("undefined / null / false girişleri yok sayar", () => {
    expect(cn("foo", undefined, null, false, "bar")).toBe("foo bar");
  });

  it("boş çağrı boş string döndürür", () => {
    expect(cn()).toBe("");
  });

  it("obje sözdizimini destekler", () => {
    expect(cn({ "text-red-500": true, "text-blue-500": false })).toBe("text-red-500");
  });

  it("dizi sözdizimini destekler", () => {
    expect(cn(["flex", "items-center"])).toBe("flex items-center");
  });
});
