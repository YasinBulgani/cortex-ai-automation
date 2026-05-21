"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type WizardColumn = {
  id: number;
  name: string;
  type: string;
  unique: boolean;
  references?: string;
  values?: string;
};
type WizardTable = { id: number; name: string; rowCount: number; columns: WizardColumn[] };
type ParsedSchema = { tables: WizardTable[]; confidence: number; warnings: string[] };

const TYPE_COLOR: Record<string, string> = {
  auto_increment: "bg-purple-900/20 text-purple-400",
  uuid:           "bg-purple-900/20 text-purple-400",
  foreign_key:    "bg-blue-900/20 text-blue-400",
  email:          "bg-green-900/20 text-green-400",
  phone:          "bg-green-900/20 text-green-400",
  enum:           "bg-orange-900/20 text-orange-400",
  integer:        "bg-slate-900/20 text-slate-400",
  decimal:        "bg-slate-900/20 text-slate-400",
  date:           "bg-cyan-900/20 text-cyan-400",
  string:         "bg-gray-900/20 text-gray-400",
};

type Step = 1 | 2 | 3 | 4 | 5;
type SourceMode = "ddl" | "db_connection" | "csv" | "natural_language";
type EnrichmentResult = {
  tables: WizardTable[];
  relationships: Array<{ from: string; to: string; type: string }>;
};
type SimResult = {
  rows_generated: number;
  tables: Array<{ name: string; rows: number }>;
};

const STEPS = [
  { n: 1, icon: "📥", label: "Kaynak Seç" },
  { n: 2, icon: "🔍", label: "Veriyi Getir" },
  { n: 3, icon: "🧠", label: "AI Zenginleştir" },
  { n: 4, icon: "✏️", label: "Düzenle" },
  { n: 5, icon: "🚀", label: "Simüle Et" },
] as const;

const SOURCE_CARDS: Array<{ mode: SourceMode; icon: string; title: string; desc: string; example: string }> = [
  { mode: "ddl", icon: "📄", title: "DDL / SQL", desc: "CREATE TABLE ifadelerini yapıştırın", example: "CREATE TABLE users (..." },
  { mode: "db_connection", icon: "🔌", title: "Veritabanı", desc: "Direkt bağlantı ile şema çekin", example: "postgresql://..." },
  { mode: "csv", icon: "📊", title: "CSV / TSV", desc: "Başlıkları ve örnek satırları yapıştırın", example: "id,email,..." },
  { mode: "natural_language", icon: "💬", title: "Doğal Dil", desc: "Tablolarınızı Türkçe anlatın", example: "Kullanıcılar ve siparişler var..." },
];

export default function VeriKaynagi() {
  const [inputText, setInputText] = useState("");
  const [parseLoading, setParseLoading] = useState(false);
  const [parseErr, setParseErr] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedSchema | null>(null);
  const [step, setStep] = useState<Step>(1);
  const [mode, setMode] = useState<SourceMode>("ddl");
  const [domainHint, setDomainHint] = useState("");
  const [tableName, setTableName] = useState("");

  /* DB Bağlantısı — extra fields */
  const [connString,     setConnString]     = useState("postgresql://twai_user:twai_pass@postgres:5432/syndata_db");
  const [schemaName,     setSchemaName]     = useState("public");
  const [excludeTables,  setExcludeTables]  = useState("alembic_version");

  /* Step 3 — enrich */
  const [enrichLoading, setEnrichLoading] = useState(false);
  const [enrichErr,     setEnrichErr]     = useState<string | null>(null);
  const [enriched,      setEnriched]      = useState<EnrichmentResult | null>(null);

  /* Step 4 — editable final tables */
  const [finalTables,  setFinalTables]  = useState<WizardTable[]>([]);
  const [activeTable,  setActiveTable]  = useState(0);

  /* Step 5 — simulation results */
  const [simLoading,   setSimLoading]   = useState(false);
  const [simErr,       setSimErr]       = useState<string | null>(null);
  const [simResult,    setSimResult]    = useState<SimResult | null>(null);
  const [activeSimTbl, setActiveSimTbl] = useState(0);

  /* Step 5 — DB write */
  const [dbWriteConn,  setDbWriteConn]  = useState("");
  const [dbWriting,    setDbWriting]    = useState(false);
  const [dbWriteErr,   setDbWriteErr]   = useState<string | null>(null);
  const [dbWriteOk,    setDbWriteOk]    = useState<Record<string, number> | null>(null);

  /* ── Helpers ──────────────────────────────────────────────────── */
  function goStep(s: Step) { setStep(s); }

  function canProceedStep2() {
    if (mode === "db_connection") return connString.trim().length >= 10;
    return inputText.trim().length >= 5;
  }

  /* ── Step 2 → 3: Parse ───────────────────────────────────────── */
  async function handleParse() {
    if (!inputText.trim()) { setParseErr("DDL ifadesini girin"); return; }
    setParseLoading(true); setParseErr(null); setParsed(null);
    try {
      const res = await apiFetch<ParsedSchema>(
        "/api/v1/tspm/test-data/parse-schema",
        { method: "POST", json: { ddl: inputText } },
      );
      setParsed(res);
    } catch (err) {
      setParseErr(err instanceof Error ? err.message : "Ayrıştırma başarısız");
    } finally {
      setParseLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6" data-testid="veri-kaynagi-page">
      <PageHeader
        icon={<span className="text-lg">🔌</span>}
        title="Veri Kaynağı"
        description="DDL yapıştırarak veritabanı şemanızı analiz edin"
      />

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">🔌 Veri Kaynağı</h1>
        <p className="text-sm text-slate-400">Veritabanı şemanızı bağlayın, AI anlasın, simülasyona hazırlayın</p>
      </div>

      {/* Step bar */}
      <div className="flex items-center gap-0">
        {STEPS.map((s, idx) => (
          <div key={s.n} className="flex items-center flex-1 last:flex-none">
            <button
              type="button"
              onClick={() => step > s.n && goStep(s.n as Step)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors
                ${step === s.n
                  ? "bg-blue-500/10 text-blue-400"
                  : step > s.n
                    ? "text-white cursor-pointer hover:bg-slate-800/30"
                    : "text-slate-400/50 cursor-default"}`}
            >
              <span className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold
                ${step === s.n
                  ? "bg-blue-600 text-white"
                  : step > s.n
                    ? "bg-blue-500/20 text-blue-400"
                    : "border border-slate-800 text-slate-400/50"}`}>
                {step > s.n ? "✓" : s.n}
              </span>
              <span className="hidden sm:inline">{s.icon} {s.label}</span>
            </button>
            {idx < STEPS.length - 1 && (
              <div className={`h-px flex-1 mx-1 transition-colors ${step > s.n ? "bg-blue-600/30" : "bg-border"}`} />
            )}
          </div>
        ))}
      </div>

      {/* ═══ Step 1: Kaynak Seç ═══ */}
      {step === 1 && (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">Veritabanı şemanızı nasıl sağlayacaksınız?</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {SOURCE_CARDS.map((card) => (
              <button
                key={card.mode}
                type="button"
                onClick={() => setMode(card.mode)}
                className={`rounded-xl border-2 p-5 text-left transition-all
                  ${mode === card.mode
                    ? "border-blue-500 bg-blue-500/5 shadow-sm"
                    : "border-slate-800 hover:border-blue-500/40 hover:bg-slate-800/20"}`}
              >
                <div className="text-2xl mb-2">{card.icon}</div>
                <p className="text-sm font-semibold">{card.title}</p>
                <p className="text-xs text-slate-400 mt-1">{card.desc}</p>
                <p className="text-[10px] text-slate-400/60 mt-2 font-mono">{card.example}</p>
              </button>
            ))}
          </div>

          {/* Hızlı başlangıç ipucu */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 bg-slate-800/30 p-4 text-xs space-y-2">
            <p className="font-medium text-slate-400">💡 Hızlı test için:</p>
            <p className="text-slate-400/80">
              {mode === "db_connection" && "Lokaldeki PostgreSQL'inize direkt bağlanın — şema otomatik çekilir"}
              {mode === "ddl" && "Northwind örnek DB'sini indirin: "}
              {mode === "csv" && "CSV başlıklarınızı + 3-5 örnek satırınızı yapıştırın"}
              {mode === "natural_language" && "Tablolarınızı ve ilişkilerini kısaca Türkçe anlatın"}
            </p>
            {mode === "db_connection" && (
              <div className="space-y-1">
                <code className="block rounded bg-slate-800 bg-slate-800 px-3 py-1.5 text-[11px] font-mono text-slate-400">
                  postgresql://twai_user:twai_pass@postgres:5432/syndata_db
                </code>
                <p className="text-[10px] text-slate-400">
                  Docker içinde servis adı <code className="font-mono">postgres</code> kullanın — <code className="font-mono">localhost</code> değil.
                  Dış bağlantı için host IP veya domain adresini girin.
                </p>
              </div>
            )}
            {mode === "ddl" && (
              <code className="block rounded bg-slate-800 bg-slate-800 px-3 py-1.5 text-[11px] font-mono text-slate-400">
                curl -o northwind.sql https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql
              </code>
            )}
          </div>

          <div className="flex justify-end">
            <Button type="button" onClick={() => goStep(2)}>
              Devam →
            </Button>
          </div>
        </div>
      )}

      {/* ═══ Step 2: Veriyi Getir ═══ */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">{SOURCE_CARDS.find(c => c.mode === mode)?.icon}</span>
            <p className="text-sm font-medium">{SOURCE_CARDS.find(c => c.mode === mode)?.title} girin</p>
          </div>

          {/* ── DB Bağlantısı formu ─────────────────────────── */}
          {mode === "db_connection" ? (
            <div className="space-y-3">
              {/* Connection string */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Bağlantı Dizesi</label>
                <Input
                  value={connString}
                  onChange={e => setConnString(e.target.value)}
                  autoFocus
                  placeholder="postgresql://kullanıcı:şifre@localhost:5432/veritabani"
                  className="font-mono text-xs"
                />
                <p className="text-[11px] text-slate-400/70">
                  Docker: <code className="bg-slate-800 bg-slate-800 px-1 rounded">postgresql://twai_user:twai_pass@postgres:5432/syndata_db</code> &nbsp;|&nbsp; Dış: <code className="bg-slate-800 bg-slate-800 px-1 rounded">postgresql://user:pass@192.168.1.10:5432/mydb</code>
                </p>
              </div>

              {/* Schema name */}
              <div className="flex items-center gap-3">
                <label className="text-xs text-slate-400 shrink-0">Şema:</label>
                <Input
                  value={schemaName}
                  onChange={e => setSchemaName(e.target.value)}
                  placeholder="public"
                  className="h-8 w-32 text-xs font-mono"
                />
              </div>

              {/* Exclude tables */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Hariç Tutulacak Tablolar (virgülle ayır)</label>
                <textarea
                  rows={3}
                  value={excludeTables}
                  onChange={e => setExcludeTables(e.target.value)}
                  placeholder="alembic_version, tspm_projects, ..."
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[11px] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
                <p className="text-[11px] text-slate-400/70">Hariç tutmak istediğiniz tabloları virgülle yazın. Boş bırakırsanız tüm tablolar çekilir.</p>
              </div>

              {/* Domain hint */}
              <Input
                value={domainHint}
                onChange={e => setDomainHint(e.target.value)}
                placeholder="Domain ipucu (isteğe bağlı): e-ticaret, bankacılık, sağlık…"
                className="text-xs"
              />
            </div>
          ) : (
            <>
              {mode === "csv" && (
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 shrink-0">Tablo Adı:</span>
                  <Input
                    value={tableName}
                    onChange={e => setTableName(e.target.value)}
                    placeholder="tablo_adi"
                    className="h-8 w-36 text-xs font-mono"
                  />
                </div>
              )}

              <textarea
                rows={mode === "natural_language" ? 5 : 12}
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                autoFocus
                placeholder={
                  mode === "ddl"
                    ? `-- Northwind, Chinook, kendi projeniz... her DDL çalışır\nCREATE TABLE customers (\n  customer_id SERIAL PRIMARY KEY,\n  company_name VARCHAR(40) NOT NULL,\n  contact_name VARCHAR(30),\n  country VARCHAR(15)\n);\n\nCREATE TABLE orders (\n  order_id SERIAL PRIMARY KEY,\n  customer_id INTEGER REFERENCES customers(customer_id),\n  order_date DATE,\n  total DECIMAL(10,2)\n);`
                    : mode === "csv"
                    ? `id,email,yas,sehir,durum\n1,ali@example.com,34,İstanbul,aktif\n2,ayse@example.com,28,Ankara,pasif\n3,mehmet@example.com,45,İzmir,aktif`
                    : `E-ticaret sistemim var. Kullanıcılar kayıt olabiliyor. Her kullanıcının birden fazla siparişi olabilir. Siparişlerin durumu beklemede, kargoda, teslim edildi veya iptal olabilir. Her siparişte birden fazla ürün bulunabilir.`
                }
                className="w-full rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-xs font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/40 min-h-[160px]"
              />

              <div className="flex items-center gap-3">
                <Input
                  value={domainHint}
                  onChange={e => setDomainHint(e.target.value)}
                  placeholder="Domain ipucu (isteğe bağlı): e-ticaret, bankacılık, sağlık, lojistik…"
                  className="flex-1 text-xs"
                />
              </div>
            </>
          )}

          {parseErr && (
            <p className="text-xs text-red-600 bg-red-900/10 border border-red-800 rounded-lg px-3 py-2">
              {parseErr}
            </p>
          )}

          <Button
            type="button"
            onClick={handleParse}
            disabled={parseLoading || !inputText.trim()}
            className="w-full"
            data-testid="btn-parse"
          >
            {parseLoading ? "Analiz ediliyor…" : "Şemayı Analiz Et"}
          </Button>
        </div>
      )}

      {/* Parsed schema preview */}
      {parsed && (
        <section className="rounded-lg border border-slate-800 overflow-hidden" data-testid="schema-preview">
          <div className="flex items-center gap-3 border-b border-slate-800 bg-slate-800/30 px-4 py-3">
            <span className="text-sm font-medium">{parsed.tables.length} tablo tespit edildi</span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                parsed.confidence >= 0.8
                  ? "bg-emerald-900/30 text-emerald-400"
                  : parsed.confidence >= 0.5
                    ? "bg-yellow-900/30 text-yellow-400"
                    : "bg-red-900/30 text-red-400"
              }`}
            >
              %{Math.round(parsed.confidence * 100)} güven
            </span>
          </div>

          {parsed.warnings.length > 0 && (
            <div className="px-4 py-3 border-b border-slate-800 bg-yellow-900/10 space-y-1">
              {parsed.warnings.map((w, i) => (
                <p key={i} className="text-xs text-yellow-400">⚠️ {w}</p>
              ))}
            </div>
          )}

          <div className="divide-y divide-slate-800">
            {parsed.tables.map((tbl) => {
              const fkCols = tbl.columns.filter((c) => c.type === "foreign_key");
              return (
                <div key={tbl.id} className="px-4 py-4 space-y-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-sm font-semibold font-mono">{tbl.name}</span>
                    <span className="text-xs text-slate-400">{tbl.columns.length} kolon</span>
                    {fkCols.map((fc) => (
                      <span
                        key={fc.id}
                        className="rounded bg-blue-900/20 border border-blue-800 px-1.5 py-0.5 text-[10px] font-mono text-blue-400"
                      >
                        {fc.name} → {fc.references}
                      </span>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {tbl.columns.map((c) => (
                      <span
                        key={c.id}
                        className={`rounded border border-slate-700 px-2 py-0.5 text-[11px] font-mono ${
                          TYPE_COLOR[c.type] ?? "bg-gray-900/20 text-gray-400"
                        }`}
                      >
                        {c.name}
                        <span className="opacity-50 ml-1">:{c.type}</span>
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
