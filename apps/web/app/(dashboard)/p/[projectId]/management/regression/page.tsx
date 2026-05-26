"use client";

import { useMemo, useState } from "react";

import {
  useCreateManagementRun,
  useCreateRegressionSet,
  useManagementCycles,
  useManagementRepository,
  useRegressionSets,
  useSuggestRegressionCandidates,
  type RegressionCandidate,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

const PRIORITIES = ["P0", "P1", "P2", "P3"];
const SEVERITIES = ["blocker", "critical", "major", "minor"];
const TYPES = ["functional", "regression", "smoke", "uat", "exploratory"];

function toggle(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

export default function ManagementRegressionPage({ params }: { params: { projectId: string } }) {
  const repository = useManagementRepository(params.projectId);
  const cycles = useManagementCycles(params.projectId);
  const sets = useRegressionSets(params.projectId);
  const suggest = useSuggestRegressionCandidates(params.projectId);
  const createSet = useCreateRegressionSet(params.projectId);
  const createRun = useCreateManagementRun(params.projectId);
  const [name, setName] = useState(`Regression ${new Date().toLocaleDateString("tr-TR")}`);
  const [description, setDescription] = useState("");
  const [priorities, setPriorities] = useState<string[]>(["P0", "P1"]);
  const [severities, setSeverities] = useState<string[]>(["blocker", "critical", "major"]);
  const [types, setTypes] = useState<string[]>(["functional", "regression", "smoke"]);
  const [tagText, setTagText] = useState("");
  const [includeLastFailed, setIncludeLastFailed] = useState(true);
  const [includeNotRun, setIncludeNotRun] = useState(true);
  const [includeWithoutRequirements, setIncludeWithoutRequirements] = useState(false);
  const [maxCases, setMaxCases] = useState(80);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [cycleId, setCycleId] = useState("");
  const candidates = suggest.data ?? [];
  const selectedCandidates = useMemo(
    () => candidates.filter((item) => selectedIds.includes(item.case_id)),
    [candidates, selectedIds],
  );
  const savedCaseCount = sets.data?.reduce((sum, item) => sum + item.cases.length, 0) ?? 0;

  const filters = {
    priorities,
    severities,
    types,
    tags: tagText.split(",").map((tag) => tag.trim()).filter(Boolean),
    include_last_failed: includeLastFailed,
    include_not_run: includeNotRun,
    include_without_requirements: includeWithoutRequirements,
    max_cases: maxCases,
  };

  const runSuggest = async () => {
    const result = await suggest.mutateAsync(filters);
    setSelectedIds(result.map((item) => item.case_id));
  };

  const saveSet = async () => {
    const rows = selectedCandidates.map((item, index) => ({
      case_id: item.case_id,
      order_index: index,
      risk_score: item.risk_score,
      reason: item.reasons.join(", "),
      include_mode: "manual",
    }));
    await createSet.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      filters,
      cases: rows,
    });
  };

  const startRun = async () => {
    const selectedCycle = cycleId || cycles.data?.[0]?.id;
    if (!selectedCycle || selectedIds.length === 0) return;
    const run = await createRun.mutateAsync({
      cycle_id: selectedCycle,
      name: `${name.trim() || "Regression"} Run`,
      case_ids: selectedIds,
      source_type: "regression_builder",
      source_ref: null,
      scope_snapshot: {
        regression_set_name: name.trim() || "Regression",
        filters,
        case_count: selectedCandidates.length,
        cases: selectedCandidates.map((item) => ({
          case_id: item.case_id,
          case_key: item.case_key,
          title: item.title,
          risk_score: item.risk_score,
          reasons: item.reasons,
        })),
      },
    });
    window.location.href = `/p/${params.projectId}/management/runs/${run.id}/execute`;
  };

  return (
    <ManagementShell
      projectId={params.projectId}
      title="Regression Set Builder"
      description="Risk, son koşu, priority, severity, type ve tag kurallarına göre regresyon kapsamı üretin; kapsamı set olarak saklayıp run başlatın."
      active="management/regression"
    >
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Repository Cases" value={repository.isLoading ? "..." : String(repository.data?.cases.length ?? 0)} note="aday havuz" />
        <ManagementStat label="Suggestions" value={suggest.isPending ? "..." : String(candidates.length)} note="son öneri" />
        <ManagementStat label="Selected" value={String(selectedIds.length)} note="run kapsamı" />
        <ManagementStat label="Saved Sets" value={String(sets.data?.length ?? 0)} note={`${savedCaseCount} case snapshot`} />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <ManagementPanel title="Kapsam Kuralları">
          <div className="space-y-4">
            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Set adı</span>
              <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-teal-500" />
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Açıklama</span>
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={2} className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-teal-500" />
            </label>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</p>
              <div className="flex flex-wrap gap-2">{PRIORITIES.map((item) => (
                <button key={item} type="button" onClick={() => setPriorities((value) => toggle(value, item))} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${priorities.includes(item) ? "bg-teal-500 text-slate-950" : "bg-slate-800 text-slate-300"}`}>{item}</button>
              ))}</div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Severity</p>
              <div className="flex flex-wrap gap-2">{SEVERITIES.map((item) => (
                <button key={item} type="button" onClick={() => setSeverities((value) => toggle(value, item))} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${severities.includes(item) ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-300"}`}>{item}</button>
              ))}</div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Type</p>
              <div className="flex flex-wrap gap-2">{TYPES.map((item) => (
                <button key={item} type="button" onClick={() => setTypes((value) => toggle(value, item))} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${types.includes(item) ? "bg-violet-500 text-white" : "bg-slate-800 text-slate-300"}`}>{item}</button>
              ))}</div>
            </div>
            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</span>
              <input value={tagText} onChange={(event) => setTagText(event.target.value)} placeholder="login, payment, critical-path" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-teal-500" />
            </label>
            <div className="space-y-2 text-sm text-slate-300">
              <label className="flex items-center gap-2"><input type="checkbox" checked={includeLastFailed} onChange={(event) => setIncludeLastFailed(event.target.checked)} /> Son failed/blocked/retest case'leri dahil et</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={includeNotRun} onChange={(event) => setIncludeNotRun(event.target.checked)} /> Hiç koşulmamış case'lere ağırlık ver</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={includeWithoutRequirements} onChange={(event) => setIncludeWithoutRequirements(event.target.checked)} /> Requirement bağlantısı olmayanları risk olarak işaretle</label>
            </div>
            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Maksimum case</span>
              <input type="number" min={1} max={1000} value={maxCases} onChange={(event) => setMaxCases(Number(event.target.value))} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-teal-500" />
            </label>
            <button onClick={runSuggest} disabled={suggest.isPending} className="w-full rounded-lg bg-teal-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-400 disabled:opacity-40">
              {suggest.isPending ? "Öneriler üretiliyor..." : "Regresyon Kapsamı Üret"}
            </button>
          </div>
        </ManagementPanel>

        <ManagementPanel title="Önerilen Kapsam">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">
              <button type="button" onClick={() => setSelectedIds(candidates.map((item) => item.case_id))} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">Tümünü Seç</button>
              <button type="button" onClick={() => setSelectedIds([])} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">Temizle</button>
            </div>
            <div className="flex gap-2">
              <button onClick={saveSet} disabled={createSet.isPending || !name.trim() || selectedIds.length === 0} className="rounded-lg border border-teal-500/40 px-3 py-1.5 text-xs font-semibold text-teal-200 hover:bg-teal-500/10 disabled:opacity-40">{createSet.isPending ? "Kaydediliyor..." : "Seti Kaydet"}</button>
              <select value={cycleId} onChange={(event) => setCycleId(event.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white">
                <option value="">Cycle seç</option>
                {(cycles.data ?? []).map((cycle) => <option key={cycle.id} value={cycle.id}>{cycle.name}</option>)}
              </select>
              <button onClick={startRun} disabled={createRun.isPending || selectedIds.length === 0 || !(cycleId || cycles.data?.[0]?.id)} className="rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40">Run Başlat</button>
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="px-3 py-2">Seç</th><th>Case</th><th>Risk</th><th>Meta</th><th>Gerekçe</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {candidates.map((item: RegressionCandidate) => (
                  <tr key={item.case_id} className="hover:bg-slate-950/50">
                    <td className="px-3 py-2"><input type="checkbox" checked={selectedIds.includes(item.case_id)} onChange={() => setSelectedIds((value) => toggle(value, item.case_id))} /></td>
                    <td className="px-3 py-2">
                      <p className="font-mono text-xs text-slate-500">{item.case_key}</p>
                      <p className="max-w-md truncate text-slate-200">{item.title}</p>
                    </td>
                    <td className="px-3 py-2 font-semibold text-amber-300">{item.risk_score}</td>
                    <td className="px-3 py-2 text-xs text-slate-400">{item.priority} · {item.severity} · {item.type} · {item.last_run_status ?? "not_run"}</td>
                    <td className="px-3 py-2 text-xs text-slate-400">{item.reasons.join(", ")}</td>
                  </tr>
                ))}
                {!suggest.isPending && candidates.length === 0 ? (
                  <tr><td colSpan={5} className="px-3 py-8 text-center text-sm text-slate-500">Henüz öneri üretilmedi.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </ManagementPanel>
      </div>

      <div className="mt-4">
        <ManagementPanel title="Kayıtlı Regression Setleri">
          <div className="grid gap-3 lg:grid-cols-2">
            {(sets.data ?? []).map((set) => (
              <div key={set.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-white">{set.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{new Date(set.created_at).toLocaleString("tr-TR")}</p>
                  </div>
                  <span className="rounded-full bg-teal-500/10 px-2 py-0.5 text-xs text-teal-300">{set.cases.length} case</span>
                </div>
                {set.description ? <p className="mt-2 text-sm text-slate-400">{set.description}</p> : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  {set.cases.slice(0, 6).map((item) => <span key={item.id} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">{item.case_key}</span>)}
                </div>
              </div>
            ))}
            {!sets.isLoading && (sets.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-500">Henüz kayıtlı regression set yok.</p>
            ) : null}
          </div>
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
