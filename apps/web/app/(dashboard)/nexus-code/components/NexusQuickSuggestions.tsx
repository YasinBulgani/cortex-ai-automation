"use client";

interface Suggestion {
  label: string;
  icon: string;
  prompt: string;
}

const QUICK_SUGGESTIONS: Suggestion[] = [
  {
    label: "Sayfa Yapısı Analizi",
    icon: "🏗",
    prompt:
      "Sadece SAYFA / KOD YAPISI ANALİZİ bölümünü üret: bileşen hiyerarşisi, input tipleri, aksiyonlar, loading/error state, responsive yapı ve UI/UX dikkat noktaları.",
  },
  {
    label: "İçerik Envanteri",
    icon: "📋",
    prompt:
      "Sadece İÇERİK ENVANTERİ bölümünü üret: başlıklar, buton metinleri, placeholder, hata/başarı mesajları, tablo kolonları ve yetki mesajları.",
  },
  {
    label: "Kod Analizi",
    icon: "</>",
    prompt:
      "Sadece KOD ANALİZİ bölümünü üret: teknoloji stack, API çağrıları, validasyon noktaları, auth/rol kontrolleri, state yönetimi ve riskli alanlar.",
  },
  {
    label: "Kullanıcı Akışları",
    icon: "🔀",
    prompt:
      "Sadece KULLANICI AKIŞLARI bölümünü üret: giriş/çıkış, listeleme, CRUD, dosya işlemleri, onay/red ve hata akışları.",
  },
  {
    label: "Manuel Test Senaryoları",
    icon: "🧪",
    prompt:
      "Sadece MANUEL TEST SENARYOLARI bölümünü üret. Pozitif, negatif, boundary, validasyon, yetki ve hata senaryolarını TC-XXX formatında tam olarak listele.",
  },
  {
    label: "Bug Tahminleri",
    icon: "🐛",
    prompt:
      "Sadece BUG TAHMİNİ bölümünü üret: edge case hataları, validasyon açıkları, yetki bypass riskleri, performans riskleri, veri tutarsızlığı ve bankacılık bağlamı riskleri.",
  },
  {
    label: "Otomasyon Önerileri",
    icon: "🤖",
    prompt:
      "Sadece OTOMASYON ÖNERİSİ bölümünü üret: her kritik senaryo için araç seçimi (Playwright/Cypress/Selenium/Karate), gerekçe ve örnek test kodu.",
  },
  {
    label: "Özet & Aksiyon",
    icon: "📊",
    prompt:
      "Sadece ÇIKTI ÖZETİ bölümünü üret: toplam senaryo sayısı, yüksek riskli alanlar, smoke test seti (3-5 senaryo), otomasyon öncelik sırası ve QA aksiyon listesi.",
  },
];

interface NexusQuickSuggestionsProps {
  onSelect: (prompt: string) => void;
}

export function NexusQuickSuggestions({ onSelect }: NexusQuickSuggestionsProps) {
  return (
    <div className="grid grid-cols-2 gap-2.5 text-xs sm:grid-cols-4">
      {QUICK_SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          type="button"
          onClick={() => onSelect(s.prompt)}
          className="flex flex-col items-start gap-1.5 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-left transition hover:border-violet-500/40 hover:bg-violet-500/8 hover:text-violet-200 text-slate-500"
        >
          <span className="text-base leading-none">{s.icon}</span>
          <span className="leading-snug">{s.label}</span>
        </button>
      ))}
    </div>
  );
}
