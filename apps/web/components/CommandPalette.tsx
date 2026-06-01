"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { useProjects } from "@/lib/hooks";
import { useScenarios } from "@/lib/hooks/use-scenarios";
import { useProject } from "@/lib/useProject";
import { PRODUCT_FAMILY, PRODUCT_FAMILY_STORAGE_KEY, getSegmentLabel } from "@/lib/product";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import { productMeta } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

const RECENT_STORAGE_KEY = "neurex_command_recent";
const MAX_RECENT = 5;

// ─── İkonlar ────────────────────────────────────────────────────────────────

function IcChart()    { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M7 16l4-4 4 4 6-6" /></svg>; }
function IcFolder()   { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>; }
function IcEdit()     { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>; }
function IcFlow()     { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" /></svg>; }
function IcBrain()    { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>; }
function IcTerminal() { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M8 9l-4 3 4 3M16 9l4 3-4 3M13 5l-2 14" /></svg>; }
function IcBook()     { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>; }
function IcDatabase() { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>; }
function IcSettings() { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>; }
function IcPlus()     { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>; }
function IcRefresh()  { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>; }
function IcClock()    { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>; }
function IcSearch()   { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>; }

// ─── Navigation komutları ───────────────────────────────────────────────────

interface NavCommand {
  id: string;
  label: string;
  hint?: string;
  href: string;
  icon: React.ReactNode;
  keywords?: string;
  shortcut?: string;
}

const NAV_COMMANDS: NavCommand[] = [
  { id: "nav-home",     label: "Aktivite Monitörü", hint: "Ana panel — sistem durumu",   href: "/",              icon: <IcChart />,    keywords: "home panel dashboard aktivite",       shortcut: "G A" },
  { id: "nav-projects", label: "Projeler",          hint: "Tüm projeler portfolio",      href: "/portfolio",     icon: <IcFolder />,   keywords: "portfolio proje workspace",            shortcut: "G P" },
  { id: "nav-drafts",   label: "Senaryo Oluşturucu",hint: "AI ile senaryo taslakla",     href: "/task-drafts",   icon: <IcEdit />,     keywords: "senaryo task draft scenario",          shortcut: "G S" },
  { id: "nav-flows",    label: "Akış Tasarımcısı",  hint: "Akış şablonları",             href: "/flow-designer", icon: <IcFlow />,     keywords: "flow akış designer şablon template" },
  { id: "nav-agents",   label: "AI Ajanları",       hint: "Akıllı ajanlar katalogu",     href: "/ai-agents",     icon: <IcBrain />,    keywords: "ai agent ajan", shortcut: "G I" },
  { id: "nav-prompt",   label: "Prompt Registry",   hint: "Prompt veritabanı ve rollout", href: "/admin/prompts", icon: <IcTerminal />, keywords: "prompt registry kütüphane rollout" },
  { id: "nav-dsl",      label: "DSL Kataloğu",      hint: "DSL bilgi merkezi",           href: "/dsl-catalog",   icon: <IcBook />,     keywords: "dsl katalog sözlük step library" },
  { id: "nav-data",     label: "Veri Merkezi",      hint: "Sentetik veri kaynak yönetimi",href: "/veri-kaynagi", icon: <IcDatabase />, keywords: "veri data sentetik synthetic" },
  { id: "nav-sim",      label: "Veri Simülatörü",   hint: "Sentetik veri üret ve indir", href: "/veri-simulatoru",icon: <IcDatabase />,keywords: "veri simulatör sentetik faker csv json" },
  { id: "nav-wizard",   label: "Platform Sihirbazı",hint: "Platforma hızlı başlangıç",   href: "/bgtest-wizard", icon: <IcPlus />,     keywords: "wizard sihirbaz başlangıç platform onboarding setup" },
  { id: "nav-ide",      label: "Senaryo IDE",       hint: "Test editörü",                href: "/ide",           icon: <IcTerminal />, keywords: "ide editör senaryo kod",               shortcut: "G E" },
  { id: "nav-settings", label: "Ayarlar",           hint: "Sistem yapılandırması",       href: "/admin/settings",icon: <IcSettings />, keywords: "ayar settings yapılandırma" },
  { id: "nav-security", label: "Güvenlik / 2FA",   hint: "MFA ve şifre ayarları",        href: "/settings/security", icon: <IcSettings />, keywords: "güvenlik security mfa 2fa totp şifre parola" },
];

// Aksiyon komutları (sayfa açar veya işlem yapar)
interface ActionCommand {
  id: string;
  label: string;
  hint?: string;
  href?: string;
  onRun?: () => void;
  icon: React.ReactNode;
  keywords?: string;
}

// ─── localStorage recent helpers ────────────────────────────────────────────

type RecentEntry = { id: string; label: string; href: string; ts: number };

function loadRecent(): RecentEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (!raw) return [];
    return (JSON.parse(raw) as RecentEntry[]).slice(0, MAX_RECENT);
  } catch { return []; }
}

function saveRecent(entry: Omit<RecentEntry, "ts">) {
  if (typeof window === "undefined") return;
  try {
    const list = loadRecent().filter(r => r.id !== entry.id);
    list.unshift({ ...entry, ts: Date.now() });
    localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(list.slice(0, MAX_RECENT)));
  } catch { /* ignore */ }
}

// ─── Component ──────────────────────────────────────────────────────────────

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { data: projects = [] } = useProjects();
  const { project } = useProject();
  const [recent, setRecent] = useState<RecentEntry[]>([]);

  // Senaryo araması — aktif proje varsa ve query ≥2 karakter ise
  const scenarioQuery = query.trim().length >= 2 ? query.trim() : "";
  const { data: scenarioPage } = useScenarios(
    project?.id && scenarioQuery ? project.id : undefined,
    { search: scenarioQuery, page_size: 6 },
  );
  const scenarioCommands = useMemo(
    () =>
      (scenarioPage?.items ?? []).map((s) => ({
        id: `scenario-${s.id}`,
        label: s.title,
        hint: s.status ?? "senaryo",
        href: `/p/${project?.id}/scenarios/${s.id}`,
        icon: <IcEdit />,
        keywords: `${s.title} ${s.description ?? ""} senaryo scenario`,
      })),
    [scenarioPage, project?.id],
  );

  // Cmd+K / Ctrl+K toggle + Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(prev => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Açıldığında recent yükle, kapandığında query sıfırla
  useEffect(() => {
    if (open) setRecent(loadRecent());
    else setQuery("");
  }, [open]);

  const runCommand = useCallback((cmd: { id: string; label: string; href?: string; onRun?: () => void }) => {
    setOpen(false);
    if (cmd.href) {
      saveRecent({ id: cmd.id, label: cmd.label, href: cmd.href });
      router.push(cmd.href);
    } else if (cmd.onRun) {
      cmd.onRun();
    }
  }, [router]);

  // Aksiyon komutları
  const actionCommands: ActionCommand[] = useMemo(() => [
    { id: "act-new-project",  label: "Yeni Proje Oluştur",        hint: "Sihirbazı aç",          href: "/new-project",        icon: <IcPlus />,    keywords: "new project yeni proje create" },
    { id: "act-new-scenario", label: "Yeni Senaryo",              hint: "Aktif projeye senaryo", href: project?.id ? `/p/${project.id}/scenarios/new` : "/task-drafts", icon: <IcPlus />, keywords: "new scenario yeni senaryo" },
    { id: "act-refresh",      label: "Sayfayı Yenile",            hint: "Hard reload",           onRun: () => location.reload(),                            icon: <IcRefresh />, keywords: "refresh yenile reload" },
    { id: "act-clear-product",label: "Ürün Odağını Temizle (Tümü)",hint: "Tüm ürünlere dön",      onRun: () => { localStorage.removeItem(PRODUCT_FAMILY_STORAGE_KEY); location.reload(); }, icon: <IcRefresh />, keywords: "ürün all tümü clear reset" },
  ], [project]);

  // Proje quick switcher (en çok 8 göster)
  const projectCommands = useMemo(
    () => projects.slice(0, 8).map(p => ({
      id: `proj-${p.id}`,
      label: p.name,
      hint: "Projeye geç",
      href: `/p/${p.id}/scenarios`,
      icon: <IcFolder />,
      keywords: `${p.name} ${p.description ?? ""} proje project`,
    })),
    [projects],
  );

  // Ürün quick switcher
  const productCommands = useMemo(
    () => PRODUCT_FAMILY.map(p => ({
      id: `prod-${p.id}`,
      label: p.name,
      hint: p.tagline,
      onRun: () => {
        localStorage.setItem(PRODUCT_FAMILY_STORAGE_KEY, p.id);
        setOpen(false);
        router.push(`/products/${p.id}`);
      },
      icon: <span className="text-base leading-none">{productMeta[p.id].emoji}</span>,
      keywords: `${p.name} ${p.tagline} ${p.id} ürün product`,
    })),
    [router],
  );

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Komut paleti"
      className="fixed inset-0 z-modal flex items-start justify-center pt-[15vh] px-4"
      shouldFilter
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in" onClick={() => setOpen(false)} />

      {/* Palet kart */}
      <div className="relative w-full max-w-2xl rounded-xl border border-border-strong bg-surface-overlay shadow-xl animate-scale-in overflow-hidden">

        {/* Search header */}
        <div className="flex items-center gap-2 border-b border-border px-4">
          <IcSearch />
          <Command.Input
            value={query}
            onValueChange={setQuery}
            placeholder="Komut yaz, sayfa ara, projeye git…"
            className="flex-1 h-12 bg-transparent text-sm text-fg placeholder-fg-subtle focus:outline-none"
          />
          <KbdGroup>
            <Kbd size="sm">Esc</Kbd>
          </KbdGroup>
        </div>

        {/* Liste */}
        <Command.List className="max-h-[60vh] overflow-y-auto py-2">
          <Command.Empty className="py-12 text-center text-sm text-fg-subtle">
            Sonuç bulunamadı.
            <p className="mt-1 text-xs text-fg-disabled">Farklı bir kelime dene veya proje adı yaz</p>
          </Command.Empty>

          {/* Son kullanılanlar — sadece query boşken */}
          {!query && recent.length > 0 && (
            <Command.Group heading={<GroupHeader icon={<IcClock />} label="Son Kullanılan" />}>
              {recent.map(r => (
                <CommandItem
                  key={r.id}
                  value={`${r.id} ${r.label}`}
                  onSelect={() => runCommand({ id: r.id, label: r.label, href: r.href })}
                  icon={<IcClock />}
                  label={r.label}
                  hint={timeAgo(r.ts)}
                />
              ))}
            </Command.Group>
          )}

          {/* Sayfalara git */}
          <Command.Group heading={<GroupHeader label="Git" />}>
            {NAV_COMMANDS.map(c => (
              <CommandItem
                key={c.id}
                value={`${c.label} ${c.keywords ?? ""}`}
                onSelect={() => runCommand(c)}
                icon={c.icon}
                label={c.label}
                hint={c.hint}
                shortcut={c.shortcut}
              />
            ))}
          </Command.Group>

          {/* Aksiyonlar */}
          <Command.Group heading={<GroupHeader label="Yap" />}>
            {actionCommands.map(c => (
              <CommandItem
                key={c.id}
                value={`${c.label} ${c.keywords ?? ""}`}
                onSelect={() => runCommand(c)}
                icon={c.icon}
                label={c.label}
                hint={c.hint}
              />
            ))}
          </Command.Group>

          {/* Senaryo arama — query ≥2 ve aktif proje varsa */}
          {scenarioCommands.length > 0 && (
            <Command.Group heading={<GroupHeader icon={<IcEdit />} label={`Senaryo · ${project?.name ?? ""}`} />}>
              {scenarioCommands.map((c) => (
                <CommandItem
                  key={c.id}
                  value={`${c.label} ${c.keywords}`}
                  onSelect={() => runCommand(c)}
                  icon={c.icon}
                  label={c.label}
                  hint={c.hint}
                />
              ))}
            </Command.Group>
          )}

          {/* Proje switcher */}
          {projectCommands.length > 0 && (
            <Command.Group heading={<GroupHeader label="Projeye Geç" />}>
              {projectCommands.map(c => (
                <CommandItem
                  key={c.id}
                  value={`${c.label} ${c.keywords}`}
                  onSelect={() => runCommand(c)}
                  icon={c.icon}
                  label={c.label}
                  hint={c.hint}
                />
              ))}
            </Command.Group>
          )}

          {/* Ürün switcher */}
          <Command.Group heading={<GroupHeader label="Ürüne Geç" />}>
            {productCommands.map(c => (
              <CommandItem
                key={c.id}
                value={`${c.label} ${c.keywords}`}
                onSelect={() => runCommand(c)}
                icon={c.icon}
                label={c.label}
                hint={c.hint}
              />
            ))}
          </Command.Group>
        </Command.List>

        {/* Footer */}
        <div className="border-t border-border px-4 py-2 flex items-center justify-between text-[11px] text-fg-subtle">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <KbdGroup><Kbd size="sm">↑</Kbd><Kbd size="sm">↓</Kbd></KbdGroup>
              gezin
            </span>
            <span className="flex items-center gap-1">
              <Kbd size="sm">↵</Kbd>
              seç
            </span>
            <span className="flex items-center gap-1">
              <Kbd size="sm">Esc</Kbd>
              kapat
            </span>
          </div>
          <span>{NAV_COMMANDS.length + actionCommands.length + projects.length + PRODUCT_FAMILY.length} komut</span>
        </div>
      </div>
    </Command.Dialog>
  );
}

// ─── Yardımcı bileşenler ────────────────────────────────────────────────────

function GroupHeader({ icon, label }: { icon?: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
      {icon}
      {label}
    </div>
  );
}

function CommandItem({
  value, onSelect, icon, label, hint, shortcut,
}: {
  value: string;
  onSelect: () => void;
  icon: React.ReactNode;
  label: string;
  hint?: string;
  shortcut?: string;
}) {
  return (
    <Command.Item
      value={value}
      onSelect={onSelect}
      className={cn(
        "group flex items-center gap-3 mx-2 my-0.5 px-3 py-2 rounded-md cursor-pointer text-sm text-fg-muted",
        "data-[selected=true]:bg-brand-soft data-[selected=true]:text-fg",
      )}
    >
      <span className="text-fg-subtle group-data-[selected=true]:text-brand-primary">
        {icon}
      </span>
      <span className="flex-1 min-w-0 truncate">{label}</span>
      {hint && (
        <span className="hidden sm:block text-xs text-fg-subtle truncate max-w-[40%]">{hint}</span>
      )}
      {shortcut && (
        <KbdGroup>
          {shortcut.split(" ").map(k => <Kbd key={k} size="sm">{k}</Kbd>)}
        </KbdGroup>
      )}
    </Command.Item>
  );
}

function timeAgo(ts: number): string {
  const diff = (Date.now() - ts) / 1000;
  if (diff < 60) return "az önce";
  if (diff < 3600) return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  return `${Math.floor(diff / 86400)} gün önce`;
}
