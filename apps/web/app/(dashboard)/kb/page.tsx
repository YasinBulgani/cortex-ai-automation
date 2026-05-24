"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useKnowledgeBase, type KbArticle } from "@/lib/useKnowledgeBase";

const CATEGORIES = [
  { id: "general", label: "Genel", icon: "📚" },
  { id: "getting-started", label: "Başlangıç", icon: "🚀" },
  { id: "how-to", label: "Nasıl Yapılır", icon: "🔧" },
  { id: "troubleshooting", label: "Sorun Giderme", icon: "🛟" },
  { id: "best-practices", label: "İyi Uygulamalar", icon: "✨" },
  { id: "api", label: "API", icon: "🔌" },
  { id: "compliance", label: "Uyum", icon: "🛡️" },
];

const SEED_ARTICLES: Omit<KbArticle, "id" | "created_at" | "updated_at" | "view_count" | "helpful_count" | "unhelpful_count" | "author_id" | "author_name">[] = [
  {
    title: "İlk senaryomu nasıl yazarım?",
    body:
      "## 3 Yol Var\n\n" +
      "1. **Manuel:** Senaryolar → Yeni Senaryo → form doldur\n" +
      "2. **AI ile (önerilen):** Sıfır Bilgi → URL/PDF/Swagger gir → 9 AI ajanı senaryo üretir\n" +
      "3. **Recorder:** Recorder → tarayıcıyı kaydet, kod otomatik üretilir\n\n" +
      "AI yolu hızlı sonuç verir; manuel daha kontrollü.",
    tags: ["scenario", "başlangıç", "ai"],
    category: "getting-started",
  },
  {
    title: "Test koştu, fail oldu — ne yapayım?",
    body:
      "## Tanı adımları\n\n" +
      "1. Execution detail sayfasında **screenshot + video**'ya bak\n" +
      "2. **AI Debug Report** butonuna tıkla — otomatik analiz çıkar\n" +
      "3. Healer agent **locator değişti** dediyse → 'Düzelt' butonu\n" +
      "4. Sorun değişen UI değilse → senaryo step'ini düzenle veya manuel inceleme\n\n" +
      "Sadece başarısız senaryoları tekrar koşmak için: detail sayfasında **'Failed-only Re-run'**.",
    tags: ["failure", "debug", "healer"],
    category: "troubleshooting",
  },
  {
    title: "Flaky test nasıl tespit edilir?",
    body:
      "## Otomatik tespit\n\n" +
      "Flaky → koşumdan koşuma farklı sonuç veren testler. Sistem otomatik flip-rate + duration variance + recent fail rate ile **flakiness score** üretir.\n\n" +
      "**Flaky** sayfasında: skoru > %50 olanlar **quarantine** önerilir. Otomatik karantina için: Settings → Auto-quarantine threshold.\n\n" +
      "Quarantine'de olan testler scheduled koşumlardan otomatik dışlanır.",
    tags: ["flaky", "quality", "karantina"],
    category: "best-practices",
  },
  {
    title: "Türkçe BDD nasıl yazılır?",
    body:
      "## Verildi / Yapılınca / Sonra\n\n" +
      "Türkçe yazabilirsin; sistem otomatik Gherkin'e çevirir:\n\n" +
      "```\n" +
      "Senaryo: Login akışı\n" +
      "  Verildi kullanıcı login sayfasındadır\n" +
      "  Yapılınca geçerli credentials girilir\n" +
      "  Sonra dashboard'a yönlendirilir\n" +
      "```\n\n" +
      "Eşdeğer Gherkin:\n\n" +
      "```\n" +
      "Scenario: Login akışı\n" +
      "  Given user is on login page\n" +
      "  When valid credentials are entered\n" +
      "  Then redirected to dashboard\n" +
      "```",
    tags: ["bdd", "gherkin", "türkçe"],
    category: "how-to",
  },
  {
    title: "CI/CD'ye nasıl entegre ederim?",
    body:
      "## GitHub Actions örneği\n\n" +
      "```yaml\n" +
      "- name: Trigger Neurex test\n" +
      "  run: |\n" +
      "    curl -X POST $NEUREX_URL/api/v1/tspm/projects/$PROJECT/executions \\\n" +
      "      -H \"Authorization: Bearer $NEUREX_TOKEN\" \\\n" +
      "      -d '{\"scenario_ids\": [\"smoke-suite\"]}'\n" +
      "```\n\n" +
      "**CLI ile:**\n" +
      "```\n" +
      "neurex runs trigger -p proj-1 -s scenario-id-1\n" +
      "```\n\n" +
      "Webhook için: Integrations → Webhooks → 'GitHub Actions' template.",
    tags: ["ci", "cd", "github", "automation"],
    category: "how-to",
  },
  {
    title: "KVKK uyum dokümanı nerede?",
    body:
      "## Compliance dosyaları\n\n" +
      "- `docs/compliance/kvkk.md` — Kişisel Veri Envanteri + saklama süreleri\n" +
      "- `docs/compliance/bddk-checklist.md` — BDDK Md.7/9/14/16 kontrol matrisi\n" +
      "- `docs/compliance/soc2-control-matrix.md` — SOC 2 Type II hazırlık\n" +
      "- `docs/compliance/iso27001-controls.md` — ISO 27001 Annex A controls\n\n" +
      "Veri silme talebi (KVKK Md.11(e)): `POST /api/v1/privacy/erasure-request`",
    tags: ["kvkk", "bddk", "uyum"],
    category: "compliance",
  },
];

export default function KnowledgeBasePage() {
  const { articles, list, search, create } = useKnowledgeBase();
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [seededOnce, setSeededOnce] = useState(false);

  // Auto-seed sample articles on first mount — moved to useEffect to avoid
  // calling setState during render (infinite re-render loop risk).
  useEffect(() => {
    if (articles.length === 0 && !seededOnce) {
      setSeededOnce(true);
      SEED_ARTICLES.forEach((a) =>
        create({ ...a, author_id: "neurex", author_name: "Neurex" }),
      );
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const visible = query.trim()
    ? search(query)
    : list({ category: activeCategory ?? undefined });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" data-testid="kb-page">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">📚 Knowledge Base</h1>
          <p className="mt-2 text-sm text-slate-400">
            Sorularına yanıt — başlangıç rehberleri, nasıl-yapılır, sorun giderme.
          </p>
        </header>

        <div className="mb-6">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="🔍 Ara: 'flaky', 'CI/CD', 'KVKK', ..."
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm focus:border-indigo-500 focus:outline-none"
            data-testid="kb-search-input"
          />
        </div>

        {!query.trim() && (
          <div className="mb-6 flex flex-wrap gap-2" data-testid="kb-categories">
            <button
              type="button"
              onClick={() => setActiveCategory(null)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                activeCategory === null
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-700 text-slate-400 hover:bg-slate-800"
              }`}
              data-testid="kb-category-all"
            >
              Tümü
            </button>
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setActiveCategory(c.id)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                  activeCategory === c.id
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-700 text-slate-400 hover:bg-slate-800"
                }`}
                data-testid={`kb-category-${c.id}`}
              >
                {c.icon} {c.label}
              </button>
            ))}
          </div>
        )}

        {visible.length === 0 ? (
          <div
            className="rounded-xl border border-dashed border-slate-700 p-12 text-center"
            data-testid="kb-empty"
          >
            <div className="text-4xl">📭</div>
            <p className="mt-3 text-sm text-slate-400">
              {query.trim() ? `"${query}" için sonuç yok` : "Bu kategoride makale yok"}
            </p>
          </div>
        ) : (
          <ul className="space-y-3" data-testid="kb-article-list">
            {visible.map((a) => (
              <li
                key={a.id}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:bg-slate-900/60"
                data-testid={`kb-article-${a.id}`}
              >
                <Link href={`/kb/${a.id}`} className="block">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-semibold text-white">{a.title}</h3>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-400">
                        {a.body.replace(/[#*`]/g, "").slice(0, 160)}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
                        <span>{CATEGORIES.find((c) => c.id === a.category)?.label ?? a.category}</span>
                        <span>·</span>
                        <span>{a.view_count} görüntüleme</span>
                        {a.helpful_count > 0 && (
                          <>
                            <span>·</span>
                            <span>👍 {a.helpful_count}</span>
                          </>
                        )}
                        {a.tags.slice(0, 3).map((t) => (
                          <span key={t} className="rounded bg-slate-800 px-1.5 py-0.5">
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
