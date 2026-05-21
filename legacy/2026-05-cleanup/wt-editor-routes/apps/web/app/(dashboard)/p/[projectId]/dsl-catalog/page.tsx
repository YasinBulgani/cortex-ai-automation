"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api-client";
import {
  dslApi,
  type DslAction,
  type DslCategoryNode,
  type DslLang,
  type DslStats,
} from "@/lib/dsl-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

// ── Tipler ────────────────────────────────────────────────────────────────

type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ok"; data: T }
  | { status: "error"; error: string };

// ── Sayfa ─────────────────────────────────────────────────────────────────

export default function DslCatalogPage() {
  const [stats, setStats] = useState<LoadState<DslStats>>({ status: "idle" });
  const [tree, setTree] = useState<LoadState<DslCategoryNode[]>>({
    status: "idle",
  });
  const [actions, setActions] = useState<LoadState<DslAction[]>>({
    status: "idle",
  });
  const [total, setTotal] = useState(0);

  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedLang, setSelectedLang] = useState<DslLang | "">("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selected, setSelected] = useState<DslAction | null>(null);
  const [reloading, setReloading] = useState(false);

  const loadStats = useCallback(async () => {
    setStats({ status: "loading" });
    try {
      const data = await dslApi.stats();
      setStats({ status: "ok", data });
    } catch (err) {
      setStats({ status: "error", error: toMessage(err) });
    }
  }, []);

  const loadTree = useCallback(async () => {
    setTree({ status: "loading" });
    try {
      const data = await dslApi.categories();
      setTree({ status: "ok", data });
    } catch (err) {
      setTree({ status: "error", error: toMessage(err) });
    }
  }, []);

  const loadActions = useCallback(async () => {
    setActions({ status: "loading" });
    try {
      if (searchTerm.trim()) {
        const res = await dslApi.search({
          q: searchTerm.trim(),
          lang: selectedLang || undefined,
          limit: 200,
        });
        const items = res.items.map((h) => h.action);
        setActions({ status: "ok", data: items });
        setTotal(res.total);
      } else {
        const res = await dslApi.listActions({
          category: selectedCategory || undefined,
          lang: selectedLang || undefined,
          page: 1,
          page_size: 200,
        });
        setActions({ status: "ok", data: res.items });
        setTotal(res.total);
      }
    } catch (err) {
      setActions({ status: "error", error: toMessage(err) });
    }
  }, [searchTerm, selectedCategory, selectedLang]);

  useEffect(() => {
    loadStats();
    loadTree();
  }, [loadStats, loadTree]);

  useEffect(() => {
    loadActions();
  }, [loadActions]);

  const onReload = useCallback(async () => {
    setReloading(true);
    try {
      await dslApi.reload();
      await Promise.all([loadStats(), loadTree(), loadActions()]);
    } catch (err) {
      alert(`Reload hatası: ${toMessage(err)}`);
    } finally {
      setReloading(false);
    }
  }, [loadStats, loadTree, loadActions]);

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <Header
        stats={stats}
        onReload={onReload}
        reloading={reloading}
      />

      <div className="flex flex-1 gap-4 overflow-hidden">
        <aside className="w-64 shrink-0 overflow-y-auto rounded border border-slate-800 bg-slate-950/50 p-3">
          <CategoryTree
            tree={tree}
            selected={selectedCategory}
            onSelect={(id) => {
              setSelectedCategory(id);
              setSearchTerm("");
            }}
          />
        </aside>

        <section className="flex flex-1 flex-col overflow-hidden rounded border border-slate-800 bg-slate-950/50">
          <Toolbar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            selectedLang={selectedLang}
            onLangChange={setSelectedLang}
            total={total}
            selectedCategory={selectedCategory}
            onClearCategory={() => setSelectedCategory("")}
          />

          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-y-auto">
              <ActionList
                actions={actions}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
              />
            </div>

            <aside className="w-[28rem] shrink-0 overflow-y-auto border-l border-slate-800 bg-slate-950/80 p-4">
              <ActionDetail action={selected} />
            </aside>
          </div>
        </section>
      </div>
    </div>
  );
}

// ── Header ────────────────────────────────────────────────────────────────

function Header({
  stats,
  onReload,
  reloading,
}: {
  stats: LoadState<DslStats>;
  onReload: () => void;
  reloading: boolean;
}) {
  const summary = useMemo(() => {
    if (stats.status !== "ok") return null;
    const s = stats.data;
    return {
      total: s.total,
      tr: s.aliases?.tr ?? 0,
      en: s.aliases?.en ?? 0,
      both: s.aliases?.both ?? 0,
      impls: Object.entries(s.by_implementation || {})
        .map(([k, v]) => `${k}:${v}`)
        .join("  ·  "),
      loadedAt: s.loaded_at,
    };
  }, [stats]);

  return (
    <header className="flex items-center justify-between gap-4 rounded border border-slate-800 bg-slate-950/50 px-5 py-3">
      <div>
        <h1 className="text-lg font-semibold text-white">DSL Katalogu</h1>
        <p className="text-xs text-slate-400">
          Tüm test cümlecikleri tek sözlükte — TR + EN + implementasyon yolu.
        </p>
      </div>

      <div className="flex items-center gap-6 text-xs text-slate-400">
        {stats.status === "loading" && <span>Yükleniyor…</span>}
        {stats.status === "error" && (
          <span className="text-red-400">Hata: {stats.error}</span>
        )}
        {summary && (
          <>
            <Metric label="Toplam" value={String(summary.total)} />
            <Metric label="TR" value={String(summary.tr)} />
            <Metric label="EN" value={String(summary.en)} />
            <Metric label="TR+EN" value={String(summary.both)} />
            {summary.impls && (
              <Metric label="Impl" value={summary.impls} />
            )}
          </>
        )}
        <Button
          variant="secondary"
          size="sm"
          onClick={onReload}
          disabled={reloading}
        >
          {reloading ? "Yükleniyor…" : "Yeniden Yükle"}
        </Button>
      </div>
    </header>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <span className="font-mono text-sm text-white">{value}</span>
    </div>
  );
}

// ── Category Tree ─────────────────────────────────────────────────────────

function CategoryTree({
  tree,
  selected,
  onSelect,
}: {
  tree: LoadState<DslCategoryNode[]>;
  selected: string;
  onSelect: (id: string) => void;
}) {
  if (tree.status === "loading") {
    return <p className="text-xs text-slate-400">Kategoriler yükleniyor…</p>;
  }
  if (tree.status === "error") {
    return <p className="text-xs text-red-400">Hata: {tree.error}</p>;
  }
  if (tree.status !== "ok") return null;

  return (
    <nav className="flex flex-col gap-1 text-sm">
      <CategoryRow
        label="Tümü"
        count={tree.data.reduce((acc, n) => acc + n.count, 0)}
        active={selected === ""}
        onClick={() => onSelect("")}
      />
      {tree.data.map((node) => (
        <div key={node.id} className="flex flex-col gap-0.5">
          <CategoryRow
            label={node.label}
            count={node.count}
            active={selected === node.id}
            onClick={() => onSelect(node.id)}
            bold
          />
          {node.children.map((child) => (
            <CategoryRow
              key={child.id}
              label={child.label}
              count={child.count}
              active={selected === child.id}
              onClick={() => onSelect(child.id)}
              indent
            />
          ))}
        </div>
      ))}
    </nav>
  );
}

function CategoryRow({
  label,
  count,
  active,
  onClick,
  bold,
  indent,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  bold?: boolean;
  indent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full items-center justify-between rounded px-2 py-1 text-left transition-colors",
        active
          ? "bg-blue-600/30 text-white"
          : "text-slate-300 hover:bg-white/5",
        indent ? "pl-5" : "",
        bold ? "font-medium" : "font-normal",
      ].join(" ")}
    >
      <span className="truncate">{label}</span>
      <span className="ml-2 text-xs text-slate-500">{count}</span>
    </button>
  );
}

// ── Toolbar ───────────────────────────────────────────────────────────────

function Toolbar({
  searchTerm,
  onSearchChange,
  selectedLang,
  onLangChange,
  total,
  selectedCategory,
  onClearCategory,
}: {
  searchTerm: string;
  onSearchChange: (v: string) => void;
  selectedLang: DslLang | "";
  onLangChange: (v: DslLang | "") => void;
  total: number;
  selectedCategory: string;
  onClearCategory: () => void;
}) {
  return (
    <div className="flex items-center gap-3 border-b border-slate-800 bg-slate-950/70 px-4 py-3">
      <Input
        placeholder="Cümlecik ara: tikla, click, should be visible…"
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="max-w-md"
      />

      <select
        aria-label="Alias dili filtresi"
        value={selectedLang}
        onChange={(e) => onLangChange(e.target.value as DslLang | "")}
        className="h-10 rounded border border-slate-800 bg-slate-900 px-2 text-sm text-white"
      >
        <option value="">Tüm diller</option>
        <option value="tr">Türkçe</option>
        <option value="en">English</option>
      </select>

      {selectedCategory && (
        <button
          type="button"
          onClick={onClearCategory}
          className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
        >
          Kategori: {selectedCategory} ✕
        </button>
      )}

      <span className="ml-auto text-xs text-slate-400">
        {total.toLocaleString("tr-TR")} cümlecik
      </span>
    </div>
  );
}

// ── Action List ───────────────────────────────────────────────────────────

function ActionList({
  actions,
  selectedId,
  onSelect,
}: {
  actions: LoadState<DslAction[]>;
  selectedId: string | null;
  onSelect: (a: DslAction) => void;
}) {
  if (actions.status === "loading") {
    return <p className="p-4 text-sm text-slate-400">Yükleniyor…</p>;
  }
  if (actions.status === "error") {
    return <p className="p-4 text-sm text-red-400">Hata: {actions.error}</p>;
  }
  if (actions.status !== "ok") return null;
  if (actions.data.length === 0) {
    return (
      <p className="p-4 text-sm text-slate-400">
        Sonuç yok. Farklı bir kategori/filter/arama deneyin.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-slate-800">
      {actions.data.map((a) => {
        const langs = Object.keys(a.aliases || {}).sort().join(" / ") || "—";
        const primary =
          a.aliases?.tr?.[0] || a.aliases?.en?.[0] || a.description;
        const impls = Object.keys(a.implementations || {});
        return (
          <li
            key={a.id}
            onClick={() => onSelect(a)}
            className={[
              "cursor-pointer px-4 py-3 transition-colors",
              selectedId === a.id
                ? "bg-blue-600/20"
                : "hover:bg-white/5",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-3">
              <code className="font-mono text-sm text-white">{a.id}</code>
              <div className="flex items-center gap-2">
                <Badge>{langs}</Badge>
                {impls.map((i) => (
                  <Badge key={i} className="border-blue-700 text-blue-300">
                    {i}
                  </Badge>
                ))}
              </div>
            </div>
            <p className="mt-1 text-sm text-slate-300">{primary}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {a.category} · {a.tags?.slice(0, 4).join(", ") || "tag yok"}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

// ── Action Detail ─────────────────────────────────────────────────────────

function ActionDetail({ action }: { action: DslAction | null }) {
  if (!action) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-slate-500">
        Bir cümlecik seçin — detay burada görüntülenir.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 text-sm text-slate-200">
      <div>
        <code className="font-mono text-base text-white">{action.id}</code>
        <p className="mt-1 text-xs text-slate-400">{action.category}</p>
      </div>

      <p className="text-sm">{action.description}</p>

      <section>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Alias'lar
        </h3>
        <div className="flex flex-col gap-2">
          {Object.entries(action.aliases || {}).map(([lang, list]) => (
            <div key={lang}>
              <p className="text-xs font-semibold text-blue-300">
                {lang.toUpperCase()}
              </p>
              <ul className="ml-3 list-disc space-y-1">
                {list.map((alias, i) => (
                  <li key={i} className="text-sm text-slate-200">
                    <code className="break-words text-slate-100">{alias}</code>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {action.parameters && action.parameters.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Parametreler
          </h3>
          <ul className="ml-3 list-disc space-y-1 text-xs">
            {action.parameters.map((p) => (
              <li key={p.name}>
                <span className="font-mono text-white">{p.name}</span>{" "}
                <span className="text-slate-400">({p.type})</span>
                {p.description ? ` — ${p.description}` : ""}
                {p.required ? "" : " · opsiyonel"}
              </li>
            ))}
          </ul>
        </section>
      )}

      {action.implementations &&
        Object.keys(action.implementations).length > 0 && (
          <section>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              İmplementasyon
            </h3>
            <div className="flex flex-col gap-2 text-xs">
              {Object.entries(action.implementations).map(([lang, impl]) => (
                <div
                  key={lang}
                  className="rounded border border-slate-800 bg-slate-900/70 p-2"
                >
                  <p className="mb-1 font-semibold text-blue-300">{lang}</p>
                  <p className="break-all text-slate-300">
                    {impl.source_file}
                  </p>
                  {(impl.module || impl.class) && (
                    <p className="mt-0.5 text-slate-500">
                      {impl.module || impl.class}
                      {impl.function || impl.method
                        ? `.${impl.function || impl.method}`
                        : ""}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

      {action.tags && action.tags.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Etiketler
          </h3>
          <div className="flex flex-wrap gap-1">
            {action.tags.map((t) => (
              <Badge key={t}>{t}</Badge>
            ))}
          </div>
        </section>
      )}

      {action.examples && action.examples.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Örnekler
          </h3>
          {action.examples.map((ex, i) => (
            <pre
              key={i}
              className="overflow-x-auto rounded border border-slate-800 bg-slate-950 p-2 text-xs text-slate-200"
            >
              {ex}
            </pre>
          ))}
        </section>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────

function toMessage(err: unknown): string {
  if (err instanceof ApiError) return `${err.status} · ${err.message}`;
  if (err instanceof Error) return err.message;
  return String(err);
}
