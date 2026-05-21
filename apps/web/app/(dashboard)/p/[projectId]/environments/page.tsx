"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  useEnvironments,
  useCreateEnvironment,
  useUpdateEnvironment,
  useDeleteEnvironment,
  type ApiEnvironment,
} from "@/lib/hooks/use-api-testing";
import { useToast } from "@/components/ui/toast";

interface VarRow { key: string; value: string; sensitive?: boolean; revealed?: boolean }

const SUGGESTED_KEYS = ["base_url", "auth_token", "api_key", "timeout", "tckn", "username", "password"];

const PRESETS = [
  {
    label: "Test Ortamı",
    variables: { base_url: "https://test.example.com", timeout: "5000" },
    sensitive: [] as string[],
  },
  {
    label: "Staging Ortamı",
    variables: { base_url: "https://staging.example.com", timeout: "8000" },
    sensitive: [] as string[],
  },
  {
    label: "Üretim Ortamı",
    variables: { base_url: "https://api.example.com", timeout: "10000" },
    sensitive: [] as string[],
  },
];

function rowsToVarsAndSensitive(rows: VarRow[]): { variables: Record<string, string>; sensitive_keys: string[] } {
  const variables: Record<string, string> = {};
  const sensitive_keys: string[] = [];
  for (const row of rows) {
    if (row.key) {
      variables[row.key] = row.value;
      if (row.sensitive) sensitive_keys.push(row.key);
    }
  }
  return { variables, sensitive_keys };
}

function varsToRows(variables: Record<string, string>, sensitiveKeys: string[] = []): VarRow[] {
  return Object.entries(variables).map(([key, value]) => ({
    key,
    value,
    sensitive: sensitiveKeys.includes(key),
    revealed: false,
  }));
}

function maskedValue(value: string): string {
  if (!value) return "";
  return "••••••••••••";
}

// ── Compare modal ─────────────────────────────────────────────────────────────
function CompareModal({
  environments,
  onClose,
}: {
  environments: ApiEnvironment[];
  onClose: () => void;
}) {
  const [sel1, setSel1] = useState(environments[0]?.id ?? "");
  const [sel2, setSel2] = useState(environments[1]?.id ?? environments[0]?.id ?? "");

  const e1 = environments.find((e) => e.id === sel1);
  const e2 = environments.find((e) => e.id === sel2);

  const allKeys = Array.from(
    new Set([
      ...Object.keys(e1?.variables ?? {}),
      ...Object.keys(e2?.variables ?? {}),
    ])
  ).sort();

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-base font-semibold text-white">Ortam Karşılaştırma</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">✕</button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-xs text-slate-500 uppercase tracking-wider pt-8">Değişken</div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Ortam A</label>
              <select
                value={sel1}
                onChange={(e) => setSel1(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none"
              >
                {environments.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Ortam B</label>
              <select
                value={sel2}
                onChange={(e) => setSel2(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none"
              >
                {environments.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
          </div>
          <div className="space-y-1">
            {allKeys.map((key) => {
              const v1 = e1?.variables[key];
              const v2 = e2?.variables[key];
              const isSensitive = e1?.sensitive_keys.includes(key) || e2?.sensitive_keys.includes(key);
              const differ = v1 !== v2;
              return (
                <div key={key} className={`grid grid-cols-3 gap-4 rounded-lg px-3 py-2 ${differ ? "bg-amber-500/5 border border-amber-500/20" : "bg-slate-800/30"}`}>
                  <span className="font-mono text-xs text-slate-300 self-center">{key}</span>
                  <span className={`font-mono text-xs self-center ${v1 === undefined ? "text-slate-600 italic" : "text-white"}`}>
                    {v1 === undefined ? "—" : isSensitive ? maskedValue(v1) : v1}
                  </span>
                  <span className={`font-mono text-xs self-center ${v2 === undefined ? "text-slate-600 italic" : "text-white"}`}>
                    {v2 === undefined ? "—" : isSensitive ? maskedValue(v2) : v2}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="border-t border-slate-800 px-6 py-4 flex justify-end">
          <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:text-white">
            Kapat
          </button>
        </div>
      </div>
    </>
  );
}

export default function EnvironmentsPage() {
  const projectId = useRouteParam("projectId");
  const { toast } = useToast();

  const { data: environments = [], isLoading } = useEnvironments(projectId);
  const createMut = useCreateEnvironment(projectId);
  const updateMut = useUpdateEnvironment(projectId);
  const deleteMut = useDeleteEnvironment(projectId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editRows, setEditRows] = useState<VarRow[]>([]);
  const [editDescription, setEditDescription] = useState("");
  const [editIsDefault, setEditIsDefault] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importJson, setImportJson] = useState("");
  const [showCompare, setShowCompare] = useState(false);
  const [testConnStatus, setTestConnStatus] = useState<"idle" | "testing" | "ok" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selected = useMemo(
    () => environments.find((e) => e.id === selectedId) ?? null,
    [environments, selectedId],
  );

  const selectEnv = useCallback((env: ApiEnvironment) => {
    setSelectedId(env.id);
    setEditName(env.name);
    setEditDescription(env.description ?? "");
    setEditIsDefault(env.is_default);
    setEditRows(varsToRows(env.variables, env.sensitive_keys));
    setTestConnStatus("idle");
  }, []);

  const handleCreate = useCallback(() => {
    createMut.mutate(
      { name: "Yeni Ortam", variables: {}, is_default: false },
      {
        onSuccess: (env) => {
          toast("Ortam oluşturuldu", "success");
          selectEnv(env);
        },
        onError: () => toast("Ortam oluşturulamadı", "error"),
      },
    );
  }, [createMut, selectEnv]);

  const handleClone = useCallback(() => {
    if (!selected) return;
    const { variables, sensitive_keys } = rowsToVarsAndSensitive(editRows);
    createMut.mutate(
      {
        name: `${editName} (Kopya)`,
        description: editDescription,
        variables,
        sensitive_keys,
        is_default: false,
      },
      {
        onSuccess: (env) => {
          toast("Ortam kopyalandı", "success");
          selectEnv(env);
        },
        onError: () => toast("Kopyalama başarısız", "error"),
      },
    );
  }, [selected, editRows, editName, editDescription, createMut, selectEnv]);

  const handleSave = useCallback(() => {
    if (!selectedId) return;
    const { variables, sensitive_keys } = rowsToVarsAndSensitive(editRows);
    updateMut.mutate(
      { envId: selectedId, name: editName, description: editDescription, variables, sensitive_keys, is_default: editIsDefault },
      {
        onSuccess: () => toast("Ortam kaydedildi", "success"),
        onError: () => toast("Kaydetme başarısız", "error"),
      },
    );
  }, [selectedId, editName, editDescription, editRows, editIsDefault, updateMut]);

  const handleDelete = useCallback(
    (envId: string) => {
      deleteMut.mutate(envId, {
        onSuccess: () => {
          if (selectedId === envId) {
            setSelectedId(null);
            setEditRows([]);
          }
        },
        onError: () => toast("Silme başarısız", "error"),
      });
    },
    [deleteMut, selectedId],
  );

  // Test connection: try to fetch base_url from env variables
  const handleTestConnection = useCallback(async () => {
    const baseUrl = editRows.find((r) => r.key === "base_url")?.value;
    if (!baseUrl) {
      toast("base_url değişkeni tanımlı değil", "error");
      return;
    }
    setTestConnStatus("testing");
    try {
      await fetch(`/api/v1/proxy/health?url=${encodeURIComponent(baseUrl)}`, { signal: AbortSignal.timeout(5000) });
      setTestConnStatus("ok");
      toast("Bağlantı başarılı", "success");
    } catch {
      setTestConnStatus("error");
      toast("Bağlantı hatası", "error");
    }
  }, [editRows]);

  const addRow = useCallback(() => {
    setEditRows((prev) => [...prev, { key: "", value: "", sensitive: false, revealed: false }]);
  }, []);

  const updateRow = useCallback((idx: number, patch: Partial<VarRow>) => {
    setEditRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }, []);

  const removeRow = useCallback((idx: number) => {
    setEditRows((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const addSuggestion = useCallback((key: string) => {
    setEditRows((prev) => {
      if (prev.some((r) => r.key === key)) return prev;
      const isSensitive = ["auth_token", "api_key", "tckn", "password"].includes(key);
      return [...prev, { key, value: "", sensitive: isSensitive, revealed: false }];
    });
  }, []);

  const applyPreset = useCallback((preset: (typeof PRESETS)[number]) => {
    const newRows: VarRow[] = Object.entries(preset.variables).map(([key, value]) => ({
      key,
      value,
      sensitive: preset.sensitive.includes(key),
      revealed: false,
    }));
    setEditRows((prev) => {
      const presetKeys = new Set(Object.keys(preset.variables));
      const kept = prev.filter((r) => !presetKeys.has(r.key));
      return [...newRows, ...kept];
    });
    toast(`${preset.label} şablonu uygulandı`, "info");
  }, []);

  const handleExport = useCallback(() => {
    if (!selected) return;
    const { variables, sensitive_keys } = rowsToVarsAndSensitive(editRows);
    const payload = { name: editName, description: editDescription, variables, sensitive_keys, is_default: editIsDefault };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${editName.replace(/\s+/g, "_").toLowerCase()}_env.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("JSON olarak indirildi", "success");
  }, [selected, editRows, editName, editDescription, editIsDefault]);

  const handleImport = useCallback(() => {
    try {
      const parsed = JSON.parse(importJson);
      if (!parsed || typeof parsed !== "object") throw new Error("Geçersiz format");
      const vars: Record<string, string> = parsed.variables ?? parsed;
      const sens: string[] = parsed.sensitive_keys ?? [];
      if (typeof vars !== "object" || Array.isArray(vars)) throw new Error("Geçersiz format");
      if (parsed.name && typeof parsed.name === "string") setEditName(parsed.name);
      if (parsed.description && typeof parsed.description === "string") setEditDescription(parsed.description);
      if (typeof parsed.is_default === "boolean") setEditIsDefault(parsed.is_default);
      setEditRows(varsToRows(vars, sens));
      setShowImport(false);
      setImportJson("");
      toast("JSON başarıyla içerildi", "success");
    } catch {
      toast("Geçersiz JSON formatı", "error");
    }
  }, [importJson]);

  const handleFileImport = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => { setImportJson(reader.result as string); setShowImport(true); };
    reader.readAsText(file);
    e.target.value = "";
  }, []);

  const inputCls = "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
  const btnPrimary = "inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const btnSecondary = "inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors";

  return (
    <div className="space-y-6" data-testid="environments-page">
      {showCompare && environments.length >= 1 && (
        <CompareModal environments={environments} onClose={() => setShowCompare(false)} />
      )}

      <PageHeader
        icon={<span className="text-lg">🖥</span>}
        title="Ortam Yönetimi"
        description="API test ortamlarını oluşturun, düzenleyin ve değişkenleri yönetin."
        right={
          <div className="flex items-center gap-2 flex-wrap">
            <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleFileImport} />
            {environments.length >= 2 && (
              <button type="button" className={btnSecondary} onClick={() => setShowCompare(true)}>
                ⚖ Karşılaştır
              </button>
            )}
            {selected && (
              <>
                <button type="button" className={btnSecondary} onClick={() => fileInputRef.current?.click()}>
                  ⬆ JSON Yükle
                </button>
                <button type="button" className={btnSecondary} onClick={handleExport}>
                  ⬇ JSON İndir
                </button>
                <button type="button" className={btnSecondary} onClick={handleClone} disabled={createMut.isPending}>
                  🗐 Kopyala
                </button>
              </>
            )}
            <button type="button" className={btnPrimary} onClick={handleCreate} disabled={createMut.isPending}>
              + Yeni Ortam
            </button>
          </div>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
        </div>
      ) : environments.length === 0 && !selectedId ? (
        <EmptyState
          icon="🌍"
          title="Henüz ortam yok"
          description="API testleriniz için ortam değişkenleri tanımlamaya başlayın."
          action={
            <button type="button" className={btnPrimary} onClick={handleCreate} disabled={createMut.isPending}>
              + İlk Ortamı Oluştur
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Environment list */}
          <div className="lg:col-span-4">
            <SectionCard title="Ortamlar" right={<span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{environments.length}</span>} noPad>
              <div className="divide-y divide-slate-800">
                {environments.map((env) => (
                  <button
                    key={env.id}
                    type="button"
                    onClick={() => selectEnv(env)}
                    className={`w-full px-4 py-3 text-left transition-colors hover:bg-slate-800/60 ${selectedId === env.id ? "bg-slate-800/80 border-l-2 border-blue-500" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm font-medium text-white truncate">{env.name}</span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {env.is_default && (
                          <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-medium text-emerald-400">Varsayılan</span>
                        )}
                        {env.sensitive_keys.length > 0 && (
                          <span className="text-[10px] text-amber-400" title="Hassas değişkenler var">🔒</span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 text-[11px] text-slate-500">
                      <span>{Object.keys(env.variables).length} değişken</span>
                      {env.sensitive_keys.length > 0 && <span>{env.sensitive_keys.length} hassas</span>}
                    </div>
                  </button>
                ))}
              </div>
            </SectionCard>
          </div>

          {/* Editor panel */}
          <div className="lg:col-span-8 space-y-4">
            {!selected ? (
              <SectionCard>
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-slate-500 text-2xl mb-2">🌍</p>
                  <p className="text-sm text-slate-400">Düzenlemek için sol taraftan bir ortam seçin</p>
                </div>
              </SectionCard>
            ) : (
              <>
                {/* Info card */}
                <SectionCard title="Ortam Bilgileri">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Ortam Adı</label>
                      <input type="text" className={inputCls} value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Örneğin: Production" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Açıklama</label>
                      <input type="text" className={inputCls} value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder="Bu ortam için açıklama" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <div className="relative">
                        <input type="checkbox" className="sr-only peer" checked={editIsDefault} onChange={(e) => setEditIsDefault(e.target.checked)} />
                        <div className="h-5 w-9 rounded-full bg-slate-700 peer-checked:bg-blue-600 transition-colors after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-slate-400 after:transition-all peer-checked:after:translate-x-full peer-checked:after:bg-white" />
                      </div>
                      <span className="text-sm text-slate-300">Varsayılan ortam</span>
                    </label>

                    {/* Test connection */}
                    <button
                      type="button"
                      onClick={handleTestConnection}
                      disabled={testConnStatus === "testing"}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 ${
                        testConnStatus === "ok" ? "bg-emerald-600/20 border border-emerald-500/30 text-emerald-400" :
                        testConnStatus === "error" ? "bg-red-600/20 border border-red-500/30 text-red-400" :
                        "border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {testConnStatus === "testing" && <span className="h-3 w-3 rounded-full border border-current border-t-transparent animate-spin" />}
                      {testConnStatus === "ok" && "✓"}
                      {testConnStatus === "error" && "✗"}
                      {testConnStatus === "idle" && "🔌"}
                      {testConnStatus === "testing" ? "Test ediliyor…" :
                       testConnStatus === "ok" ? "Bağlantı başarılı" :
                       testConnStatus === "error" ? "Bağlantı hatası" :
                       "Bağlantı Test Et"}
                    </button>
                  </div>
                </SectionCard>

                {/* Presets */}
                <SectionCard title="Hızlı Şablon">
                  <div className="flex flex-wrap gap-2">
                    {PRESETS.map((p) => (
                      <button key={p.label} type="button" className={btnSecondary} onClick={() => applyPreset(p)}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                </SectionCard>

                {/* Variable editor */}
                <SectionCard
                  title="Değişkenler"
                  right={<span className="text-xs text-slate-500">{editRows.length} değişken</span>}
                >
                  {editRows.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">
                      Henüz değişken eklenmedi. Aşağıdan değişken ekleyin veya bir şablon uygulayın.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {/* Header */}
                      <div className="grid grid-cols-12 gap-2 px-1 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                        <div className="col-span-4">Anahtar</div>
                        <div className="col-span-6">Değer</div>
                        <div className="col-span-2 text-center">Eylem</div>
                      </div>
                      {editRows.map((row, idx) => (
                        <div key={idx} className="grid grid-cols-12 gap-2 items-center rounded-lg bg-slate-800/40 p-2">
                          {/* Key */}
                          <div className="col-span-4">
                            <input
                              type="text"
                              className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-xs text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                              value={row.key}
                              onChange={(e) => updateRow(idx, { key: e.target.value })}
                              placeholder="key"
                            />
                          </div>
                          {/* Value — masked if sensitive and not revealed */}
                          <div className="col-span-6 relative">
                            <input
                              type={row.sensitive && !row.revealed ? "password" : "text"}
                              className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-xs text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none pr-8"
                              value={row.value}
                              onChange={(e) => updateRow(idx, { value: e.target.value })}
                              placeholder={row.sensitive ? "••••••••" : "değer"}
                            />
                            {row.sensitive && (
                              <button
                                type="button"
                                onClick={() => updateRow(idx, { revealed: !row.revealed })}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                                title={row.revealed ? "Gizle" : "Göster"}
                              >
                                {row.revealed ? "🙈" : "👁"}
                              </button>
                            )}
                          </div>
                          {/* Actions: sensitive toggle + delete */}
                          <div className="col-span-2 flex items-center justify-center gap-1">
                            <button
                              type="button"
                              onClick={() => updateRow(idx, { sensitive: !row.sensitive })}
                              className={`rounded p-1 text-xs transition-colors ${row.sensitive ? "text-amber-400 bg-amber-500/10" : "text-slate-500 hover:text-slate-300"}`}
                              title={row.sensitive ? "Hassas (gizli)" : "Normal"}
                            >
                              {row.sensitive ? "🔒" : "🔓"}
                            </button>
                            <button
                              type="button"
                              onClick={() => removeRow(idx)}
                              className="rounded p-1 text-slate-500 hover:text-red-400 transition-colors"
                              title="Sil"
                            >
                              🗑
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add row + suggestions */}
                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <button type="button" className={btnSecondary} onClick={addRow}>
                      + Değişken Ekle
                    </button>
                    <span className="text-xs text-slate-600 mx-1">|</span>
                    {SUGGESTED_KEYS.filter((k) => !editRows.some((r) => r.key === k)).map((k) => (
                      <button
                        key={k}
                        type="button"
                        className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-0.5 text-[11px] font-mono text-slate-400 hover:border-blue-500/40 hover:text-blue-400 transition-colors"
                        onClick={() => addSuggestion(k)}
                      >
                        + {k}
                      </button>
                    ))}
                  </div>
                </SectionCard>

                {/* Import panel */}
                {showImport && (
                  <SectionCard title="JSON İçerik">
                    <textarea
                      className={`${inputCls} h-40 font-mono text-xs`}
                      value={importJson}
                      onChange={(e) => setImportJson(e.target.value)}
                      placeholder='{"variables": {"base_url": "...", "api_key": "..."}, "sensitive_keys": ["api_key"]}'
                    />
                    <div className="mt-3 flex items-center gap-2">
                      <button type="button" className={btnPrimary} onClick={handleImport}>Uygula</button>
                      <button type="button" className={btnSecondary} onClick={() => { setShowImport(false); setImportJson(""); }}>İptal</button>
                    </div>
                  </SectionCard>
                )}

                {/* Save / Delete */}
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-red-600/20 border border-red-500/30 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-600/30 transition-colors"
                    onClick={() => handleDelete(selectedId!)}
                    disabled={deleteMut.isPending}
                  >
                    🗑 Ortamı Sil
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                    onClick={handleSave}
                    disabled={updateMut.isPending || !editName.trim()}
                  >
                    {updateMut.isPending ? "Kaydediliyor…" : "Kaydet"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
