"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { DocumentUploader, type UploadedDocument } from "@/components/DocumentUploader";
import {
  DEFAULT_PRODUCT_FAMILY_ID,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_STORAGE_KEY,
  getProductFamilyMember,
  type ProductFamilyId,
} from "@/lib/product";


// ── Tip, sabit, helper ve viewer importları (modüler dosyalardan) ─────────
import type {
  AutomationFile,
  BddScenario,
  IdeFile,
  IdeFileKind,
  LocatorEntry,
  LocatorFile,
  LocatorMatch,
  LocatorMatchLlmStatus,
  LocatorMatchStatus,
  ManualTest,
  MaviyakaFeature,
  RegSet,
  SavedScenario,
  ScenarioMappingReport,
  StepMapping,
  XPathQuality,
} from "./types";
import {
  actionNeedsLocator,
  matchKey,
  NO_LOCATOR_ACTIONS,
} from "./types";
import {
  GHERKIN_KW,
  PRIORITY_COLOR,
  PRODUCT_AVAILABILITY_META,
  PRODUCT_FLOW_GUIDE,
  PRODUCT_WIZARD_PROFILE,
  STEPS,
} from "./constants";
import {
  buildFeatureFromMapping,
  buildXPathReportMd,
  maviyakaStepLine,
  slugifyProjectName,
} from "./helpers";
import { MaviyakaFeatureViewer } from "./MaviyakaFeatureViewer";

import { IdeWorkbench } from "./IdeWorkbench";


// ── Component ────────────────────────────────────────────────────────────────

export default function NewProjectPage() {
  const router = useRouter();
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeProductId, setActiveProductId] = useState<ProductFamilyId>(DEFAULT_PRODUCT_FAMILY_ID);

  // Step 2 — DB bağlantısı
  const [dbType, setDbType]       = useState("postgresql");
  const [dbHost, setDbHost]       = useState("localhost");
  const [dbPort, setDbPort]       = useState("5432");
  const [dbName, setDbName]       = useState("");
  const [dbUser, setDbUser]       = useState("");
  const [dbPass, setDbPass]       = useState("");
  const [dbConnected, setDbConnected] = useState<boolean | null>(null);

  // Step 3 — Analiz dokümanı
  const [docText, setDocText]             = useState("");
  const [extraInstructions, setExtraInstructions] = useState("");
  const [manualTests, setManualTests]     = useState<ManualTest[]>([]);
  const [bddScenarios, setBddScenarios]   = useState<BddScenario[]>([]);
  // Neurex QA Faz 2 — Yüklenen doküman
  const [uploadedDoc, setUploadedDoc]     = useState<UploadedDocument | null>(null);
  const [aiAnalysis, setAiAnalysis]       = useState<{
    modules: Array<{ name: string; description: string; test_areas: string[]; risk_level: string; estimated_test_cases: number }>;
    critical_flows: string[];
    total_estimated_cases: number;
  } | null>(null);
  const [analyzeMode, setAnalyzeMode]     = useState<"upload" | "paste">("upload");

  // Step 4 — Kayıt durumu
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);
  const [savedIds, setSavedIds]             = useState<string[]>([]);

  // Step 5 — Regresyon setleri
  const [regSets, setRegSets]         = useState<RegSet[]>([]);
  const [acceptedSets, setAcceptedSets] = useState<RegSet[]>([]);

  // Step 6 — Otomasyon seçimi
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Step 7 — Otomasyon çıktısı (fallback)
  const [featureFiles, setFeatureFiles] = useState<AutomationFile[]>([]);
  const [testFiles, setTestFiles]       = useState<AutomationFile[]>([]);
  const [activeFile, setActiveFile]     = useState<AutomationFile | null>(null);

  // Step 7 — Otomasyon kurulumu
  const [maviyakaUrl, setMaviyakaUrl]       = useState("");
  const [environment, setEnvironment]       = useState<"dev" | "test" | "qa" | "preprod" | "prod">("test");
  const [locatorFiles, setLocatorFiles]     = useState<LocatorFile[]>([]);
  const [activeLocatorFile, setActiveLocatorFile] = useState<LocatorFile | null>(null);
  const [crawling, setCrawling]             = useState(false);
  const [maviyakaFeatures, setMaviyakaFeatures] = useState<MaviyakaFeature[]>([]);
  const [activeFeatureIdx, setActiveFeatureIdx] = useState(0);
  const [testDataMap, setTestDataMap]       = useState<Record<string, string>>({});
  const [locatorModal, setLocatorModal]     = useState<{ key: string; aiSuggestion: string | null } | null>(null);
  const [running, setRunning]               = useState(false);
  const [runOutput, setRunOutput]           = useState<string | null>(null);

  const [locatorMatches, setLocatorMatches] = useState<LocatorMatch[]>([]);
  const [matchStatuses, setMatchStatuses]   = useState<Record<string, LocatorMatchStatus>>({});
  const [matching, setMatching]             = useState(false);
  const [matchScenarioCount, setMatchScenarioCount] = useState<number>(0);
  const [matchLlmStatus, setMatchLlmStatus] = useState<LocatorMatchLlmStatus | null>(null);
  const [unmatchedLocatorKeys, setUnmatchedLocatorKeys] = useState<string[]>([]);
  const [matchStats, setMatchStats] = useState<{ steps_considered: number; skipped_url_only: number } | null>(null);
  /** Aktif override popover — hangi match satırı için açık olduğu (matchKey ile) */
  const [overridePopoverKey, setOverridePopoverKey] = useState<string | null>(null);

  // Step 7 — Manuel senaryo tam eşleştirme (feature + xpath birlikte)
  const [stepMappings, setStepMappings]     = useState<ScenarioMappingReport[]>([]);
  const [matchingFull, setMatchingFull]     = useState(false);
  const [activeMappingIdx, setActiveMappingIdx] = useState(0);

  // Step 8 — Otomasyon IDE (IntelliJ benzeri)
  const [ideFiles, setIdeFiles]             = useState<IdeFile[]>([]);
  const [activeIdePath, setActiveIdePath]   = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(["features", "steps", "test-data", "locators", "pages", "config"])
  );
  const [consoleLines, setConsoleLines]     = useState<string[]>([]);
  const [ideRunning, setIdeRunning]         = useState(false);
  const [ideTab, setIdeTab]                 = useState<"console" | "problems" | "run">("console");
  const runAbortRef                         = useRef<AbortController | null>(null);

  // ── Missing declarations ──────────────────────────────────────────────────

  // Wizard step (1-9)
  const [step, setStep] = useState(1);

  // Created project ID (set after createProject succeeds)
  const [projectId, setProjectId] = useState<string | null>(null);

  // Success message state
  const [success, setSuccess] = useState<string | null>(null);

  // ── helpers ───────────────────────────────────────────────────────────────

  useEffect(() => {
    try {
      const storedProduct = localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
      if (storedProduct) setActiveProductId(getProductFamilyMember(storedProduct as ProductFamilyId).id);
    } catch {
      // ignore
    }
  }, []);

  // Step 6'ya girildiğinde kayıtlı senaryolar state'te yoksa backend'den çek.
  // (Sayfa yenilenmesi / state kaybı durumlarında liste boş kalmasın diye.)
  useEffect(() => {
    if (step !== 6) return;
    if (!projectId) return;
    if (savedScenarios.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch<Array<{ id: string; title: string; status: string }>>(
          `/api/v1/tspm/projects/${projectId}/scenarios?limit=500`
        );
        if (cancelled) return;
        const list: SavedScenario[] = (res || []).map((s) => ({
          id: s.id,
          title: s.title,
          status: s.status,
        }));
        if (list.length === 0) {
          err("Bu proje için kayıtlı senaryo bulunamadı. Analiz adımına dönüp senaryoları kaydetmen gerekiyor.");
          return;
        }
        setSavedScenarios(list);
        setSavedIds(list.map((s) => s.id));
      } catch (e: unknown) {
        if (cancelled) return;
        err(e instanceof Error ? e.message : "Senaryolar yüklenemedi");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, projectId, savedScenarios.length]);

  const selectedProduct = useMemo(
    () => getProductFamilyMember(activeProductId),
    [activeProductId],
  );
  const productGuide = PRODUCT_FLOW_GUIDE[selectedProduct.id];
  const wizardProfile = PRODUCT_WIZARD_PROFILE[selectedProduct.id];

  function projectEntryHref(nextProjectId: string | null, productId: ProductFamilyId) {
    if (!nextProjectId) return "/projects";
    const product = getProductFamilyMember(productId);
    const firstSegment = product.routeSegments[0];
    return firstSegment ? `/p/${nextProjectId}/${firstSegment}` : `/p/${nextProjectId}`;
  }

  function applyProduct(nextProductId: ProductFamilyId) {
    setActiveProductId(nextProductId);
    try {
      localStorage.setItem(PRODUCT_FAMILY_STORAGE_KEY, nextProductId);
      window.dispatchEvent(new CustomEvent("bgts-product-family-changed", { detail: nextProductId }));
    } catch {
      // ignore
    }
  }

  function notify(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 4000);
  }

  function err(msg: string) {
    setError(msg);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const dbConnectionString = `${dbType}://${dbUser}:${dbPass}@${dbHost}:${dbPort}/${dbName}`;

  // ── Step handlers ─────────────────────────────────────────────────────────

  // 1 — Proje oluştur
  async function createProject() {
    // DOM fallback: tarayıcı autofill veya event sync sorunları React state'i
    // boş bırakabiliyor; DOM'dan okuyup state'i güncelliyoruz.
    let name = projectName.trim();
    if (!name && typeof document !== "undefined") {
      const el = document.querySelector<HTMLInputElement>('input[placeholder*="deme API"]');
      if (el?.value?.trim()) {
        name = el.value.trim();
        setProjectName(name);
      }
    }
    if (!name) { err("Proje adı zorunlu"); return; }
    setLoading(true); setError(null);
    try {
      const res = await apiFetch<{ id: string }>("/api/v1/tspm/projects", {
        method: "POST",
        json: { name, description: projectDesc, primary_product_id: selectedProduct.id },
      });
      setProjectId(res.id);
      try {
        localStorage.setItem("bgts_active_project", JSON.stringify({ id: res.id, name }));
      } catch {
        // ignore
      }
      notify(`"${name}" projesi oluşturuldu — ${selectedProduct.name} odagi hazır`);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Proje oluşturulamadı");
    } finally {
      setLoading(false);
    }
  }

  // 2 — DB bağlantısı test et
  async function testDbConnection() {
    if (!dbName || !dbUser) { err("Veritabanı adı ve kullanıcı zorunlu"); return; }
    setLoading(true); setError(null); setDbConnected(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/database/test-connection`, {
        method: "POST",
        json: { connection_string: dbConnectionString, db_type: dbType },
      });
      setDbConnected(true);
      notify("Veritabanı bağlantısı başarılı");
    } catch {
      // Bağlantı endpoint'i yoksa veya bağlantı başarısızsa devam et
      setDbConnected(false);
    } finally {
      setLoading(false);
    }
  }

  function skipDb() {
    setDbConnected(null);
    setStep(3);
  }

  // 3 — Analiz & AI senaryo üretimi (Neurex QA Faz 2)
  async function runAnalysis() {
    const textToAnalyze = uploadedDoc ? uploadedDoc.full_text : docText;
    if (!textToAnalyze.trim()) {
      err(analyzeMode === "upload" ? "Önce bir doküman yükleyin" : "Doküman içeriği boş");
      return;
    }
    const mergedExtraInstructions = [wizardProfile.analysisSeed, extraInstructions.trim()]
      .filter(Boolean)
      .join("\n");
    setLoading(true); setError(null);
    try {
      // Chunk pipeline: büyük dokümanlar için chunked analiz
      if (uploadedDoc?.needs_chunking && uploadedDoc.chunk_count > 1) {
        // 1) Chunk analizi — modülleri çıkar
        const analysisRes = await apiFetch<{
          modules: Array<{ name: string; description: string; test_areas: string[]; risk_level: string; estimated_test_cases: number }>;
          critical_flows: string[];
          total_estimated_cases: number;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze-chunked`, {
          method: "POST",
          json: {
            chunks: [textToAnalyze.slice(0, 12000), textToAnalyze.slice(12000, 24000)].filter(Boolean),
            filename: uploadedDoc.filename,
            extra_instructions: mergedExtraInstructions,
          },
        });
        setAiAnalysis(analysisRes);

        // 2) Test case üretimi — normal analiz endpoint
        const res = await apiFetch<{
          manual_tests: ManualTest[];
          bdd_scenarios: BddScenario[];
          analysis_summary?: { modules: number; total_estimated: number };
          ai_provider?: string;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze`, {
          method: "POST",
          json: {
            text: textToAnalyze.slice(0, 12000), // İlk chunk
            extra_instructions: mergedExtraInstructions,
          },
        });
        setManualTests(res.manual_tests || []);
        setBddScenarios(res.bdd_scenarios || []);
        const total = (res.manual_tests?.length || 0) + (res.bdd_scenarios?.length || 0);
        notify(`${total} senaryo üretildi (${analysisRes.modules.length} modül analiz edildi)`);
      } else {
        // Normal analiz — küçük doküman
        const res = await apiFetch<{
          manual_tests: ManualTest[];
          bdd_scenarios: BddScenario[];
          analysis_summary?: { modules: number; total_estimated: number };
          ai_provider?: string;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze`, {
          method: "POST",
          json: { text: textToAnalyze, extra_instructions: mergedExtraInstructions },
        });
        setManualTests(res.manual_tests || []);
        setBddScenarios(res.bdd_scenarios || []);
        const total = (res.manual_tests?.length || 0) + (res.bdd_scenarios?.length || 0);
        if (total === 0) { err("Senaryo üretilemedi — dokümanı detaylandırın"); return; }
        const providerInfo = res.ai_provider ? ` (${res.ai_provider})` : "";
        notify(`${total} senaryo üretildi${providerInfo}`);
      }
      setStep(4);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Analiz hatası");
    } finally {
      setLoading(false);
    }
  }

  // 4 — Tüm senaryoları DB'ye kaydet
  async function saveAllScenarios() {
    setLoading(true); setError(null);
    const ids: string[] = [];
    const saved: SavedScenario[] = [];

    const allTests = [
      ...manualTests.map((t) => ({
        title: t.title,
        steps: t.steps.map((s, i) => ({
          keyword: i === 0 ? "Olduğu gibi" : i === t.steps.length - 1 ? "O zaman" : "Eğer",
          text: `${s.action} → ${s.expected}`,
        })),
      })),
      ...bddScenarios.map((s) => ({
        title: s.title,
        steps: s.steps || [],
      })),
    ];

    let lastError: string | null = null;
    for (const t of allTests) {
      try {
        const res = await apiFetch<{ id: string; title: string; status: string }>(
          `/api/v1/tspm/projects/${projectId}/scenarios`,
          { method: "POST", json: { title: t.title, description: "AI ile üretildi", status: "draft", steps: t.steps } }
        );
        ids.push(res.id);
        saved.push({ id: res.id, title: res.title, status: res.status });
      } catch (e: unknown) {
        lastError = e instanceof Error ? e.message : String(e);
      }
    }

    setSavedIds(ids);
    setSavedScenarios(saved);

    if (saved.length === 0) {
      err(`Hiçbir senaryo kaydedilemedi${lastError ? ` (${lastError})` : ""}. Lütfen tekrar deneyin.`);
      setLoading(false);
      return;
    }

    const failedCount = allTests.length - saved.length;
    if (failedCount > 0) {
      notify(`${saved.length} senaryo kaydedildi (${failedCount} tanesi başarısız)`);
    } else {
      notify(`${saved.length} senaryo kaydedildi`);
    }
    setStep(5);
    setLoading(false);
  }

  // 5 — Regresyon seti öner
  async function suggestRegSets() {
    setLoading(true); setError(null);
    try {
      const res = await apiFetch<{ sets: RegSet[] }>(
        `/api/v1/tspm/projects/${projectId}/regression-sets/suggest`,
        { method: "POST", json: { extra_instructions: "" } }
      );
      setRegSets(res.sets || []);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Öneri hatası");
    } finally {
      setLoading(false);
    }
  }

  async function acceptSets() {
    if (acceptedSets.length === 0) { err("En az bir set seçin"); return; }
    setLoading(true); setError(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/regression-sets/accept-suggestions`, {
        method: "POST",
        json: { sets: acceptedSets },
      });
      notify(`${acceptedSets.length} regresyon seti kaydedildi`);
      setStep(6);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally {
      setLoading(false);
    }
  }

  function toggleSet(set: RegSet) {
    setAcceptedSets((prev) =>
      prev.some((s) => s.name === set.name)
        ? prev.filter((s) => s.name !== set.name)
        : [...prev, set]
    );
  }

  // 6 — Otomasyon için case seç
  function toggleScenario(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function selectAll()   { setSelectedIds(new Set(savedIds)); }
  function deselectAll() { setSelectedIds(new Set()); }

  // 6 → 7: Seçili senaryolarla otomasyon kurulumuna geç
  function goToMaviyaka() {
    if (selectedIds.size === 0) { err("En az bir senaryo seçin"); return; }
    setStep(7);
  }

  // 7 — Lokator JSON dosyası yükle (multiple, module-based)
  function handleLocatorUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const parsed = JSON.parse(ev.target?.result as string);
          const locators: LocatorEntry[] = Array.isArray(parsed) ? parsed : [];
          const module = file.name.replace(/\.json$/i, "");
          const lf: LocatorFile = { name: file.name, module, locators };
          setLocatorFiles((prev) => {
            const idx = prev.findIndex((f) => f.name === file.name);
            if (idx >= 0) { const next = [...prev]; next[idx] = lf; return next; }
            return [...prev, lf];
          });
          setActiveLocatorFile(lf);
          notify(`${file.name} yüklendi — ${locators.length} lokator`);
        } catch {
          err(`${file.name} geçerli JSON değil`);
        }
      };
      reader.readAsText(file);
    });
    e.target.value = "";
  }

  // Aktif proje için tekrar kullanılabilir domain/modül slug'ı
  const projectSlug = slugifyProjectName(projectName);

  // 7 — URL'yi crawl et → lokatorları öner (+ manuel adımlarla eşleştir)
  async function crawlLocators() {
    if (!maviyakaUrl.trim()) { err("URL giriniz"); return; }
    setCrawling(true); setError(null);
    try {
      const res = await apiFetch<{ locators: LocatorEntry[] }>(
        `/api/v1/tspm/projects/${projectId}/wizard/crawl-locators`,
        { method: "POST", json: { url: maviyakaUrl, domain: projectSlug, environment } }
      );
      const lf: LocatorFile = {
        name: `${projectSlug}_${environment}_crawled.json`,
        module: projectSlug,
        locators: res.locators || [],
      };
      setLocatorFiles((prev) => [...prev, lf]);
      setActiveLocatorFile(lf);
      notify(`${lf.locators.length} lokator bulundu`);

      // Crawl sonrası seçili senaryolardaki adımlarla otomatik eşleştir
      void matchLocatorsToScenarios(lf.locators);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Crawl hatası");
    } finally {
      setCrawling(false);
    }
  }

  // 7 — Manuel test adımlarını crawl lokatorlarıyla eşleştir
  async function matchLocatorsToScenarios(locators: LocatorEntry[]) {
    if (!projectId || locators.length === 0) return;
    setMatching(true);
    try {
      const ids = Array.from(selectedIds);
      const res = await apiFetch<{
        matches: LocatorMatch[];
        unmatched_keys: string[];
        scenario_count: number;
        llm_status?: LocatorMatchLlmStatus;
        stats?: { steps_considered: number; skipped_url_only: number };
      }>(`/api/v1/tspm/projects/${projectId}/wizard/match-locators`, {
        method: "POST",
        json: {
          scenario_ids: ids.length > 0 ? ids : null,
          locators,
        },
      });
      setLocatorMatches(res.matches || []);
      setMatchStatuses(
        Object.fromEntries(
          (res.matches || []).map((m) => [matchKey(m), "pending" as LocatorMatchStatus]),
        ),
      );
      setMatchScenarioCount(res.scenario_count || 0);
      setMatchLlmStatus(res.llm_status || null);
      setUnmatchedLocatorKeys(res.unmatched_keys || []);
      setMatchStats(res.stats || null);
      if ((res.matches || []).length > 0) {
        notify(`${res.matches.length} eşleşme önerisi hazırlandı — onayına sunuldu`);
      }
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Eşleştirme hatası");
    } finally {
      setMatching(false);
    }
  }

  function setMatchStatus(key: string, status: LocatorMatchStatus) {
    setMatchStatuses((prev) => ({ ...prev, [key]: status }));
  }

  /**
   * Locator editor panelindeki ilgili key'e scroll eder, kısa süreli highlight verir.
   * Gerekirse o key'i içeren dosyayı aktif hale getirir.
   */
  function jumpToLocator(key: string) {
    const owningFile = locatorFiles.find((f) => f.locators.some((l) => l.key === key));
    if (owningFile && activeLocatorFile?.name !== owningFile.name) {
      setActiveLocatorFile(owningFile);
    }
    // DOM güncellensin diye setActiveLocatorFile sonrası microtask bekle
    requestAnimationFrame(() => {
      const el = document.getElementById(`locator-row-${key}`);
      if (!el) {
        notify(`Locator "${key}" editörde bulunamadı`);
        return;
      }
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-blue-400", "ring-offset-2", "ring-offset-slate-950");
      window.setTimeout(() => {
        el.classList.remove("ring-2", "ring-blue-400", "ring-offset-2", "ring-offset-slate-950");
      }, 1500);
    });
  }

  /**
   * Manuel override: kullanıcı aynı adıma başka bir locator key atıyor.
   * source → "manual", confidence → 1.0, xpath_quality null (recompute yok; user aware override).
   */
  function overrideMatchLocator(oldMatchKey: string, newLocatorKey: string) {
    const newLoc = locatorFiles.flatMap((f) => f.locators).find((l) => l.key === newLocatorKey);
    if (!newLoc) return;

    setLocatorMatches((prev) => {
      const next = [...prev];
      const idx = next.findIndex((m) => matchKey(m) === oldMatchKey);
      if (idx < 0) return prev;
      const old = next[idx];
      const updated: LocatorMatch = {
        ...old,
        suggested_key: newLoc.key,
        suggested_locator: { type: newLoc.type, value: newLoc.value },
        xpath_quality: null,
        confidence: 1.0,
        reason: `Manuel seçim (önceki: ${old.suggested_key})`,
        source: "manual",
      };
      next[idx] = updated;
      return next;
    });

    // Status map key değişti — eskiyi temizle, yeniyi pending→approved olarak işaretle
    setMatchStatuses((prev) => {
      const next = { ...prev };
      delete next[oldMatchKey];
      // yeni match key'i oluşturmak için mevcut match'in scenario/step'ine ihtiyacımız var
      const match = locatorMatches.find((m) => matchKey(m) === oldMatchKey);
      if (match) {
        const newKey = matchKey({ ...match, suggested_key: newLocatorKey });
        next[newKey] = "approved";
      }
      return next;
    });
    setOverridePopoverKey(null);
    notify(`Locator değiştirildi: ${newLocatorKey}`);
  }
  function approveAllMatches() {
    const LOW_CONFIDENCE_THRESHOLD = 0.6;
    const lowCount = locatorMatches.filter((m) => (m.confidence || 0) < LOW_CONFIDENCE_THRESHOLD).length;
    if (lowCount > 0) {
      const proceed = window.confirm(
        `${locatorMatches.length} öneriden ${lowCount} tanesi düşük güvenli (<%60).\n\n` +
          `Hepsini onaylarsanız zayıf heuristic eşleşmeler de kabul edilmiş olur; ` +
          `bunları tek tek gözden geçirmek daha güvenli.\n\nYine de hepsini onaylansın mı?`,
      );
      if (!proceed) return;
    }
    const next: Record<string, LocatorMatchStatus> = {};
    locatorMatches.forEach((m) => { next[matchKey(m)] = "approved"; });
    setMatchStatuses(next);
    notify(`${locatorMatches.length} eşleşme onaylandı`);
  }
  function rejectAllMatches() {
    const next: Record<string, LocatorMatchStatus> = {};
    locatorMatches.forEach((m) => { next[matchKey(m)] = "rejected"; });
    setMatchStatuses(next);
  }

  // 7 — Feature dosyaları üret (AI)
  async function generateMaviyakaFeatures() {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const allLocators = locatorFiles.flatMap((f) => f.locators);
      const res = await apiFetch<{ features: MaviyakaFeature[]; test_data: Record<string, string> }>(
        `/api/v1/tspm/projects/${projectId}/wizard/generate-maviyaka`,
        {
          method: "POST",
          json: {
            scenario_ids: Array.from(selectedIds),
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: allLocators,
          },
        }
      );
      setMaviyakaFeatures(res.features || []);
      setTestDataMap(res.test_data || {});
      setActiveFeatureIdx(0);
      notify(`${(res.features || []).length} feature dosyası üretildi`);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Feature üretim hatası");
    } finally {
      setLoading(false);
    }
  }

  // 7 — Manuel senaryoları locator kataloğuyla LLM üzerinden tam eşleştir
  //     (her step → gerçek locator key + XPath), feature'ı deterministik kur
  async function matchAndGenerateFromManual() {
    if (!projectId) return;
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      err("Önce Step 6'dan en az bir senaryo seçmelisin");
      return;
    }
    const allLocators = locatorFiles.flatMap((f) => f.locators);
    if (allLocators.length === 0) {
      err("Önce lokator dosyası yükle ya da URL'yi tara");
      return;
    }
    setMatchingFull(true); setError(null);
    try {
      const res = await apiFetch<{
        features: MaviyakaFeature[];
        mappings: ScenarioMappingReport[];
        test_data: Record<string, string>;
        catalog_size: number;
      }>(`/api/v1/tspm/projects/${projectId}/wizard/match-manual-scenarios`, {
        method: "POST",
        json: {
          scenario_ids: ids,
          url: maviyakaUrl,
          domain: projectSlug,
          environment,
          locators: allLocators,
        },
      });
      setMaviyakaFeatures(res.features || []);
      setTestDataMap((prev) => ({ ...prev, ...(res.test_data || {}) }));
      setActiveFeatureIdx(0);
      setStepMappings(res.mappings || []);
      setActiveMappingIdx(0);
      const llmCount = (res.mappings || []).filter((m) => m.llm_used).length;
      const totalSteps = (res.mappings || []).reduce((acc, m) => acc + m.steps.length, 0);
      notify(
        `${res.mappings?.length || 0} senaryo · ${totalSteps} adım eşlendi ` +
        `(${llmCount} senaryoda LLM, geri kalanı kural bazlı)`
      );
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Eşleştirme hatası");
    } finally {
      setMatchingFull(false);
    }
  }

  // 7 — Kırmızı key'e tıkla → AI lokator öner
  async function suggestLocatorForKey(key: string) {
    setLocatorModal({ key, aiSuggestion: null });
    try {
      const res = await apiFetch<{ suggestion: LocatorEntry }>(
        `/api/v1/tspm/projects/${projectId}/wizard/suggest-locator`,
        { method: "POST", json: { key, url: maviyakaUrl, domain: projectSlug, environment } }
      );
      setLocatorModal({ key, aiSuggestion: JSON.stringify(res.suggestion, null, 2) });
    } catch {
      setLocatorModal({
        key,
        aiSuggestion: JSON.stringify({ key, type: "id", value: "" }, null, 2),
      });
    }
  }

  // Adım metninden makul bir locator key türet (Türkçe → ASCII, CamelCase)
  function deriveLocatorKeyFromStep(text: string): string {
    const trMap: Record<string, string> = {
      "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
      "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
    };
    const ascii = text.split("").map((ch) => trMap[ch] ?? ch).join("");
    const stop = new Set([
      "olur", "olan", "icin", "bir", "bu", "ve", "veya", "ile", "sonra", "once",
      "kadar", "daha", "gibi", "ama", "fakat", "the", "and", "for", "into", "with",
    ]);
    const parts = ascii
      .replace(/"[^"]*"/g, " ")
      .replace(/[^a-zA-Z0-9 ]+/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 2 && !stop.has(w.toLowerCase()))
      .slice(0, 3)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
    return parts.join("") || "YeniElement";
  }

  // Bir adım için AI lokator önerisi (step metninden türetilmiş key ile)
  async function suggestLocatorForStep(step: StepMapping) {
    const key = deriveLocatorKeyFromStep(step.original);
    await suggestLocatorForKey(key);
  }

  // 7 — Lokator onayla → aktif dosyaya ekle + object repo'ya kaydet
  async function confirmLocator(entry: LocatorEntry) {
    const targetFile = activeLocatorFile ?? locatorFiles[0];
    if (!targetFile) {
      // Hiç dosya yoksa yeni bir tane oluştur
      const lf: LocatorFile = { name: "custom.json", module: "custom", locators: [entry] };
      setLocatorFiles([lf]);
      setActiveLocatorFile(lf);
    } else {
      const updated: LocatorFile = { ...targetFile, locators: [...targetFile.locators, entry] };
      setLocatorFiles((prev) => prev.map((f) => f.name === targetFile.name ? updated : f));
      setActiveLocatorFile(updated);
    }
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/locators`, {
        method: "POST",
        json: { name: entry.key, locator_value: `${entry.type}=${entry.value}`, page_url: maviyakaUrl },
      });
      setLocatorModal(null);
      notify(`"${entry.key}" kaydedildi`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error(`Locator DB'ye kaydedilemedi: "${entry.key}" —`, msg);
      err(`"${entry.key}" veritabanına kaydedilemedi. Lütfen tekrar deneyin.`);
    }
  }

  // 7 → 8: IDE dosya iskeletini üret ve editor'a geç
  function buildIdeFiles(): IdeFile[] {
    const files: IdeFile[] = [];
    const allLocators = locatorFiles.flatMap((f) => f.locators);

    // 1) .feature dosyaları — Step 7'deki stepMappings varsa her adımın üstüne
    //    XPath yorumu gömerek yeniden üret ("Element" placeholder'ı yerine gerçek
    //    locator key + XPath görünür olur).
    maviyakaFeatures.forEach((feat, i) => {
      const slug = feat.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "scenario";
      const mapping =
        stepMappings.find((m) => m.scenario_title === feat.title) ||
        stepMappings[i] ||
        null;
      const content = mapping
        ? buildFeatureFromMapping(feat.title, mapping, maviyakaUrl)
        : feat.content;
      files.push({
        path: `features/${slug}.feature`,
        name: `${slug}.feature`,
        folder: "features",
        kind: "feature",
        language: "gherkin",
        content,
      });
    });

    // 2) Step definitions (TS iskelet) — her feature için bir step defs dosyası
    maviyakaFeatures.forEach((feat) => {
      const slug = feat.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "scenario";
      const steps = (feat.content.match(/^\s*(Given|When|Then|And|But|Eğer|Olduğu gibi|O zaman|Ve)\s+.+$/gm) || [])
        .slice(0, 20)
        .map((line) => {
          const trimmed = line.trim();
          const kw = trimmed.split(/\s+/)[0] || "Given";
          const body = trimmed.slice(kw.length).trim();
          const pattern = body.replace(/"[^"]*"/g, '{string}');
          return `${kw}(/^${pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$/, async function () {\n  // TODO: implement\n  await this.page.waitForLoadState("networkidle");\n});`;
        })
        .join("\n\n");
      files.push({
        path: `steps/${slug}.steps.ts`,
        name: `${slug}.steps.ts`,
        folder: "steps",
        kind: "steps",
        language: "typescript",
        content: `import { Given, When, Then } from "@cucumber/cucumber";\nimport { expect } from "@playwright/test";\nimport locators from "../locators/${projectSlug}_${environment}.json";\nimport testData from "../test-data/${projectSlug}.data.json";\n\n${steps || "// Senaryodan step çıkarılamadı"}\n`,
      });
    });

    // 3) test-data JSON — hem test data map hem örnek
    const dataBody = {
      ...testDataMap,
      __meta: {
        url: maviyakaUrl,
        domain: projectSlug,
        environment,
        generated_at: new Date().toISOString(),
      },
    };
    files.push({
      path: `test-data/${projectSlug}.data.json`,
      name: `${projectSlug}.data.json`,
      folder: "test-data",
      kind: "data",
      language: "json",
      content: JSON.stringify(dataBody, null, 2),
    });

    // 4) locators — mevcut tüm lokator dosyalarını birleştir
    if (allLocators.length > 0) {
      files.push({
        path: `locators/${projectSlug}_${environment}.json`,
        name: `${projectSlug}_${environment}.json`,
        folder: "locators",
        kind: "locator",
        language: "json",
        content: JSON.stringify(allLocators, null, 2),
      });
    }
    locatorFiles.forEach((lf) => {
      files.push({
        path: `locators/${lf.name}`,
        name: lf.name,
        folder: "locators",
        kind: "locator",
        language: "json",
        content: JSON.stringify(lf.locators, null, 2),
      });
    });

    // 4b) xpath-report.md — Step 7'deki adım↔locator↔XPath eşleşmesini IDE'den
    //     tek dosyada görünür kılar (kırmızı satırlar locator eksikliğini işaret eder).
    if (stepMappings.length > 0) {
      files.push({
        path: `locators/xpath-report.md`,
        name: `xpath-report.md`,
        folder: "locators",
        kind: "locator",
        language: "json",
        content: buildXPathReportMd(stepMappings, maviyakaUrl, environment),
      });
    }

    // 5) pages — basit bir page object iskeleti
    files.push({
      path: `pages/${projectSlug}.page.ts`,
      name: `${projectSlug}.page.ts`,
      folder: "pages",
      kind: "page",
      language: "typescript",
      content: `import type { Page } from "@playwright/test";\nimport locators from "../locators/${projectSlug}_${environment}.json";\n\nexport class ${projectSlug.replace(/(^\w|_\w)/g, (m) => m.replace("_", "").toUpperCase())}Page {\n  constructor(private page: Page) {}\n\n  async goto() {\n    await this.page.goto(${JSON.stringify(maviyakaUrl)});\n  }\n\n${allLocators.slice(0, 12).map((l) => `  get ${l.key}() {\n    return this.page.locator(${JSON.stringify(`${l.type}=${l.value}`)});\n  }`).join("\n\n") || "  // lokator tanımlanmadı"}\n}\n`,
    });

    // 6) config — cucumber.js ve playwright.config.ts iskeletleri
    files.push({
      path: `config/cucumber.cjs`,
      name: `cucumber.cjs`,
      folder: "config",
      kind: "config",
      language: "typescript",
      content: `module.exports = {\n  default: {\n    paths: ["features/**/*.feature"],\n    require: ["steps/**/*.ts"],\n    requireModule: ["ts-node/register"],\n    format: ["progress-bar", "html:reports/cucumber.html"],\n  },\n};\n`,
    });
    files.push({
      path: `config/playwright.config.ts`,
      name: `playwright.config.ts`,
      folder: "config",
      kind: "config",
      language: "typescript",
      content: `import { defineConfig } from "@playwright/test";\n\nexport default defineConfig({\n  testDir: "./tests",\n  timeout: 30_000,\n  use: {\n    baseURL: ${JSON.stringify(maviyakaUrl)},\n    headless: true,\n    screenshot: "only-on-failure",\n    video: "retain-on-failure",\n  },\n});\n`,
    });

    return files;
  }

  function openIdeForRun() {
    if (maviyakaFeatures.length === 0) {
      err("Önce feature dosyaları üretilmeli");
      return;
    }
    const files = buildIdeFiles();
    setIdeFiles(files);
    // varsayılan açık dosya: ilk .feature
    const firstFeature = files.find((f) => f.kind === "feature");
    setActiveIdePath(firstFeature?.path || files[0]?.path || null);
    setConsoleLines([
      `[${new Date().toLocaleTimeString()}] Neurex QA Automation IDE hazırlandı`,
      `[info] ${files.length} dosya üretildi (feature + steps + data + locators + pages + config)`,
      `[info] Hedef URL: ${maviyakaUrl || "-"}  ·  Ortam: ${environment.toUpperCase()}`,
      `[hint] Sol panelden bir dosya seç, üstteki "▶ Run" ile koştur.`,
    ]);
    setStep(8);
    notify(`Otomasyon IDE açıldı — ${files.length} dosya hazır`);
  }

  function toggleFolder(folder: string) {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder);
      else next.add(folder);
      return next;
    });
  }

  async function runFromIde() {
    if (!projectId || ideFiles.filter((f) => f.kind === "feature").length === 0) return;

    // Sadece işaretli (disabled olmayan) feature'ları pytest'e gönder.
    const enabledFeatures = ideFiles.filter((f) => f.kind === "feature" && !f.disabled);
    const totalFeatures = ideFiles.filter((f) => f.kind === "feature").length;
    const skippedCount = totalFeatures - enabledFeatures.length;

    if (enabledFeatures.length === 0) {
      setConsoleLines((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] [warn] Tüm feature'lar devre dışı. Sol panelden en az birini işaretle.`,
      ]);
      return;
    }

    // Önceki bir koşum henüz sonlanmadıysa iptal et
    runAbortRef.current?.abort();
    const ctrl = new AbortController();
    runAbortRef.current = ctrl;

    setIdeRunning(true);
    setIdeTab("console");
    const featureDocs = enabledFeatures.map((f) => ({
      title: f.name.replace(/\.feature$/, ""),
      content: f.content,
    }));

    const prepend = (line: string) =>
      setConsoleLines((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${line}`]);

    prepend("▶ npx cucumber-js --config config/cucumber.cjs");
    prepend(
      `[run] ${featureDocs.length} feature dosyası koşturuluyor${
        skippedCount > 0 ? ` (${skippedCount} feature atlandı)` : ""
      }…`
    );
    try {
      const res = await apiFetch<{ output: string; passed: number; failed: number }>(
        `/api/v1/tspm/projects/${projectId}/wizard/run-maviyaka`,
        {
          method: "POST",
          signal: ctrl.signal,
          json: {
            features: featureDocs,
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: locatorFiles.flatMap((f) => f.locators),
            test_data: testDataMap,
          },
        }
      );
      const out = (res.output || "").split("\n").filter(Boolean);
      out.slice(0, 200).forEach((l) => prepend(l));
      const passed = res.passed ?? 0;
      const failed = res.failed ?? 0;
      prepend(`───────────────────────────────────────────`);
      prepend(`✓ ${passed} passed   ✗ ${failed} failed`);
      prepend(failed === 0 ? `[done] Tüm senaryolar başarılı` : `[done] ${failed} senaryo başarısız`);
      setRunOutput(res.output || `${passed} passed, ${failed} failed`);
    } catch (e: unknown) {
      // AbortError → kullanıcı durdurdu; farklı bir mesaj verelim
      const aborted =
        (e instanceof DOMException && e.name === "AbortError") ||
        (e instanceof Error && /aborted|abort/i.test(e.message));
      if (aborted) {
        prepend("[stopped] Koşum kullanıcı tarafından durduruldu");
      } else {
        const msg = e instanceof Error ? e.message : "Koşum hatası";
        prepend(`[error] ${msg}`);
      }
    } finally {
      if (runAbortRef.current === ctrl) runAbortRef.current = null;
      setIdeRunning(false);
    }
  }

  function stopFromIde() {
    if (!runAbortRef.current) return;
    runAbortRef.current.abort();
  }

  // 7 — Testleri Başlat (Python Playwright engine) — eski yol, ide geçişi için kullanılmıyor
  async function runMaviyaka() {
    if (!projectId || maviyakaFeatures.length === 0) return;
    setRunning(true); setRunOutput(null); setError(null);
    try {
      const res = await apiFetch<{ output: string; passed: number; failed: number }>(
        `/api/v1/tspm/projects/${projectId}/wizard/run-maviyaka`,
        {
          method: "POST",
          json: {
            features: maviyakaFeatures,
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: locatorFiles.flatMap((f) => f.locators),
            test_data: testDataMap,
          },
        }
      );
      setRunOutput(res.output || `${res.passed ?? 0} passed, ${res.failed ?? 0} failed`);
      setStep(9);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Çalıştırma hatası");
    } finally {
      setRunning(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[1600px] items-center gap-4 px-8 py-3">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
            data-testid="new-project-back"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Ana Sayfa
          </button>
          <span className="text-slate-700">/</span>
          <span className="text-sm font-medium">Yeni Proje</span>
          <span className="ml-auto flex items-center gap-3 text-xs text-slate-500">
            <span className="hidden sm:inline">
              Adım <span className="font-semibold text-slate-300">{step}</span> / {STEPS.length}
            </span>
            <span className="h-1.5 w-32 overflow-hidden rounded-full bg-slate-800">
              <span
                className="block h-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
                style={{ width: `${(step / STEPS.length) * 100}%` }}
              />
            </span>
          </span>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        {/* Bildirimler */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-400">
            ⚠️ {error}
            <button className="ml-3 opacity-60 hover:opacity-100" onClick={() => setError(null)}>✕</button>
          </div>
        )}
        {success && (
          <div className="mb-6 rounded-xl border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-400">
            ✓ {success}
          </div>
        )}

        {/* Mobile ürün bandı — sadece md altı */}
        <div className="mb-6 rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4 md:hidden">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-200/80">Neurex Product Focus</p>
          <div className="mt-2 flex items-center gap-2">
            <h2 className="text-lg font-semibold text-white">{selectedProduct.name}</h2>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
              {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
            </span>
          </div>
          <p className="mt-1 text-sm text-violet-200/90">{selectedProduct.tagline}</p>
          <div className="mt-3 grid grid-cols-2 gap-1.5">
            {PRODUCT_FAMILY.map((product) => (
              <button
                key={product.id}
                type="button"
                onClick={() => applyProduct(product.id)}
                className={`rounded-lg border px-2 py-1.5 text-left transition ${
                  product.id === selectedProduct.id
                    ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                    : "border-slate-800 bg-slate-900/60 text-slate-300"
                }`}
              >
                <span className="block text-[10px] font-semibold uppercase tracking-[0.16em]">{product.shortName}</span>
                <span className="mt-0.5 block text-[11px] leading-snug">{product.tagline}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Mobile horizontal step rail — sadece md altı */}
        <div className="mb-6 overflow-x-auto pb-1 md:hidden">
          <div className="flex items-center min-w-max">
            {STEPS.map((s, i) => (
              <div key={s.id} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                      ${step === s.id ? "bg-blue-600 ring-2 ring-blue-600/30 text-white" :
                        step > s.id  ? "bg-emerald-600 text-white" :
                                       "bg-slate-800 text-slate-500"}`}
                  >
                    {step > s.id ? (
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : s.id}
                  </div>
                  <span className={`mt-1 w-14 text-center text-[9px] leading-tight
                    ${step === s.id ? "text-blue-400 font-medium" : step > s.id ? "text-emerald-600" : "text-slate-700"}`}>
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`mx-0.5 mb-4 h-px w-5 shrink-0 ${step > s.id ? "bg-emerald-600" : "bg-slate-800"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 3-kolon grid: sol step rail | orta form | sağ context paneli */}
        <div className="grid gap-6 md:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_320px] xl:gap-8 2xl:grid-cols-[280px_minmax(0,1fr)_360px]">
          {/* Sol sticky step rail (md+) */}
          <aside className="hidden md:block">
            <div className="sticky top-6 space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Kurulum Adımları
                </p>
                <ol className="mt-3 space-y-1">
                  {STEPS.map((s) => {
                    const isActive = step === s.id;
                    const isDone = step > s.id;
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => { if (isDone) setStep(s.id); }}
                          disabled={!isDone}
                          className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition ${
                            isActive
                              ? "bg-blue-500/10 ring-1 ring-inset ring-blue-500/30"
                              : isDone
                                ? "hover:bg-slate-800/60 cursor-pointer"
                                : "opacity-60 cursor-not-allowed"
                          }`}
                        >
                          <span
                            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                              ${isActive ? "bg-blue-600 text-white ring-2 ring-blue-600/30" :
                                isDone  ? "bg-emerald-600 text-white" :
                                          "bg-slate-800 text-slate-500"}`}
                          >
                            {isDone ? (
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            ) : s.id}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className={`block text-xs font-semibold leading-tight ${
                              isActive ? "text-blue-300" : isDone ? "text-emerald-400" : "text-slate-300"
                            }`}>
                              {s.label}
                            </span>
                            <span className="mt-0.5 block text-[10px] leading-tight text-slate-500">
                              {s.desc}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
                <div className="mt-3 border-t border-slate-800 pt-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
                        style={{ width: `${(step / STEPS.length) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-semibold text-slate-400">
                      {Math.round((step / STEPS.length) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Orta — asıl form içeriği */}
          <div className="min-w-0">

        {/* ── STEP 1: Proje Oluştur ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold">Projeyi Tanımla</h2>
              <p className="mt-1.5 text-sm text-slate-400">
                Projen için bir ad ve açıklama gir. Kurulum sonunda{" "}
                <span className="font-medium text-violet-300">{selectedProduct.name}</span> çalışma alanı açılacak.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 xl:hidden">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Odak akışı</p>
              <p className="mt-2 text-sm font-medium text-white">{productGuide.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{selectedProduct.description}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedProduct.routeSegments.slice(0, 5).map((segment) => (
                  <span
                    key={segment}
                    className="rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[10px] font-medium text-slate-300"
                  >
                    {segment}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">Proje Adı *</label>
                <input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  onInput={(e) => setProjectName((e.target as HTMLInputElement).value)}
                  autoComplete="off"
                  placeholder="Ör: Ödeme API Test Projesi"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">Açıklama</label>
                <textarea
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  placeholder="Projenin amacı ve kapsamı..."
                  rows={3}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>
            </div>
            <button
              onClick={createProject}
              disabled={loading}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
            >
              {loading ? "Oluşturuluyor…" : "Projeyi Oluştur →"}
            </button>
          </div>
        )}

        {/* ── STEP 3: Analiz Dokümanı ── */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Analiz Dokümanı</h2>
              <p className="mt-1 text-sm text-slate-400">
                Gereksinim belgenizi yükleyin veya yapistirin. AI; seçili urun odagini koruyarak test senaryolari ve BDD üretecek.
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Varsayilan AI odagi</p>
              <p className="mt-2 text-sm text-slate-300">{wizardProfile.analysisSeed}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {wizardProfile.analysisFocus.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[10px] font-medium text-slate-300"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>

            {/* Mod Seçici */}
            <div className="flex rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <button
                onClick={() => setAnalyzeMode("upload")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition ${
                  analyzeMode === "upload"
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                Dosya Yükle
              </button>
              <button
                onClick={() => setAnalyzeMode("paste")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition ${
                  analyzeMode === "paste"
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
                Metin Yapıştır
              </button>
            </div>

            {/* Dosya Yükleme Modu */}
            {analyzeMode === "upload" && projectId && (
              <DocumentUploader
                projectId={projectId}
                onUploaded={(doc) => {
                  setUploadedDoc(doc);
                  setDocText(doc.full_text); // Hem upload hem paste için text
                  notify(`"${doc.filename}" yüklendi — ${doc.word_count.toLocaleString()} kelime`);
                }}
                onError={err}
              />
            )}

            {/* Metin Yapıştır Modu */}
            {analyzeMode === "paste" && (
              <div className="space-y-3">
                <textarea
                  value={docText}
                  onChange={(e) => setDocText(e.target.value)}
                  placeholder={"Dokümanı buraya yapıştır…\n\nÖrnek:\n• Kullanıcı sisteme e-posta ve şifresiyle giriş yapabilmeli\n• Geçersiz şifre girilince hata mesajı görünmeli\n• Şifremi Unuttum akışı çalışmalı\n• Oturum 30 dakika sonra otomatik kapanmalı"}
                  rows={12}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none resize-none font-mono"
                />
                <p className="text-right text-xs text-slate-600">{docText.length.toLocaleString()} karakter</p>
              </div>
            )}

            {/* AI Analiz Sonuçu — modül özeti */}
            {aiAnalysis && aiAnalysis.modules.length > 0 && (
              <div className="rounded-xl border border-violet-700/30 bg-violet-950/20 p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-violet-400">
                  AI Analiz Özeti — {aiAnalysis.modules.length} Modül Tespit Edildi
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {aiAnalysis.modules.slice(0, 6).map((m, i) => (
                    <div key={i} className="rounded-lg bg-slate-900/60 p-2.5">
                      <p className="text-xs font-semibold text-white truncate">{m.name}</p>
                      <div className="mt-1 flex items-center justify-between">
                        <span className={`text-[10px] font-medium ${
                          m.risk_level === "high" ? "text-red-400" :
                          m.risk_level === "medium" ? "text-yellow-400" : "text-emerald-400"
                        }`}>
                          {m.risk_level} risk
                        </span>
                        <span className="text-[10px] text-slate-500">~{m.estimated_test_cases} test</span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Tahmini toplam: <span className="font-semibold text-slate-300">{aiAnalysis.total_estimated_cases} test case</span>
                </p>
              </div>
            )}

            {/* Ek Talimatlar */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">
                Ek Talimatlar (opsiyonel)
              </label>
              <input
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
                placeholder="Ör: Negatif senaryolara ağırlık ver, sadece login akışına odaklan"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Analiz Butonu */}
            <div className="flex items-center gap-3">
              <button
                onClick={runAnalysis}
                disabled={loading || (analyzeMode === "upload" ? !uploadedDoc : !docText.trim())}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    AI Analiz Ediyor…
                  </>
                ) : (
                  <>
                    <span>🤖</span>
                    AI ile Analiz Et →
                  </>
                )}
              </button>
              {uploadedDoc && (
                <span className="text-xs text-emerald-400">
                  ✓ {uploadedDoc.filename} ({uploadedDoc.word_count.toLocaleString()} kelime)
                </span>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 4: Manuel Testler ── */}
        {step === 4 && (
          <div className="space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold">Üretilen Testler</h2>
                <p className="mt-1 text-sm text-slate-400">
                  AI <span className="text-blue-400 font-medium">{manualTests.length} manuel test</span> ve{" "}
                  <span className="text-purple-400 font-medium">{bddScenarios.length} BDD senaryo</span> üretti.
                </p>
              </div>
              <button
                onClick={saveAllScenarios}
                disabled={loading}
                className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
              >
                {loading ? "Kaydediliyor…" : `Tümünü Kaydet (${manualTests.length + bddScenarios.length})`}
              </button>
            </div>

            {/* Manuel testler */}
            {manualTests.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Manuel Testler</h3>
                {manualTests.map((t, i) => (
                  <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="text-sm font-semibold text-white mb-3">{t.title}</p>
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-500">
                          <th className="w-6 text-left pb-2">#</th>
                          <th className="text-left pb-2">Aksiyon</th>
                          <th className="text-left pb-2">Beklenen Sonuç</th>
                        </tr>
                      </thead>
                      <tbody>
                        {t.steps.map((s, j) => (
                          <tr key={j} className="border-t border-slate-800">
                            <td className="py-2 text-slate-600">{j + 1}</td>
                            <td className="py-2 text-slate-300">{s.action}</td>
                            <td className="py-2 text-emerald-400">{s.expected}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}

            {/* BDD Senaryolar */}
            {bddScenarios.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">BDD Senaryolar</h3>
                {bddScenarios.map((s, i) => (
                  <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="text-sm font-semibold text-white mb-2">{s.title}</p>
                    {s.gherkin && (
                      <pre className="rounded-lg bg-slate-950 p-3 text-xs text-purple-300 overflow-auto">{s.gherkin}</pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── STEP 5: Regresyon Seti ── */}
        {step === 5 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Regresyon Seti</h2>
              <p className="mt-1 text-sm text-slate-400">AI, senaryoları öncelik ve kapsama göre grupluyor. Onaylamak istediklerini seç.</p>
            </div>

            {regSets.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col items-center gap-4 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600/10 text-2xl">🔁</div>
                <div>
                  <p className="text-sm font-medium text-white">AI ile Regresyon Seti Öner</p>
                  <p className="mt-1 text-xs text-slate-500">Senaryolarını önceliğe göre gruplandırıyor</p>
                </div>
                <button
                  onClick={suggestRegSets}
                  disabled={loading}
                  className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
                >
                  {loading ? (
                    <>
                      <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      AI Gruplandırıyor…
                    </>
                  ) : "Regresyon Setleri Öner"}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {regSets.map((set, i) => {
                  const isSelected = acceptedSets.some((s) => s.name === set.name);
                  return (
                    <button
                      key={i}
                      onClick={() => toggleSet(set)}
                      className={`w-full rounded-xl border p-5 text-left transition-all
                        ${isSelected
                          ? "border-blue-500 bg-blue-950/30"
                          : "border-slate-800 bg-slate-900 hover:border-slate-600"}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-white">{set.name}</span>
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${PRIORITY_COLOR[set.priority]}`}>
                              {set.priority}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{set.description}</p>
                          <p className="mt-2 text-xs text-slate-600">{set.scenario_ids.length} senaryo</p>
                        </div>
                        <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition
                          ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                          {isSelected && (
                            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}

                <div className="flex gap-3">
                  <button
                    onClick={() => setAcceptedSets(regSets)}
                    className="text-xs text-blue-400 hover:underline"
                  >
                    Tümünü Seç
                  </button>
                  <button
                    onClick={() => setAcceptedSets([])}
                    className="text-xs text-slate-500 hover:underline"
                  >
                    Tümünü Kaldır
                  </button>
                </div>

                <button
                  onClick={acceptSets}
                  disabled={loading || acceptedSets.length === 0}
                  className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
                >
                  {loading ? "Kaydediliyor…" : `Seçilenleri Kaydet (${acceptedSets.length}) →`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 6: Otomasyon Seç ── */}
        {step === 6 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Otomasyona Alınacakları Seç</h2>
              <p className="mt-1 text-sm text-slate-400">
                {wizardProfile.automationPrimary
                  ? "Hangi senaryolar için otomasyon kodu üretilsin? Sec ve devam et."
                  : wizardProfile.automationNote}
              </p>
            </div>
            {!wizardProfile.automationPrimary && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                Bu adım seçili urunde opsiyonel. Istersen dogrudan kurulumu tamamlayip daha sonra web otomasyonu ekleyebilirsin.
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={selectAll}   className="text-xs text-blue-400 hover:underline">Tümünü Seç</button>
              <button onClick={deselectAll} className="text-xs text-slate-500 hover:underline">Tümünü Kaldır</button>
              <span className="text-xs text-slate-600">{selectedIds.size} / {savedScenarios.length} seçili</span>
            </div>
            <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900 p-4">
              {savedScenarios.map((s) => {
                const isSelected = selectedIds.has(s.id);
                return (
                  <button
                    key={s.id}
                    onClick={() => toggleScenario(s.id)}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition
                      ${isSelected ? "bg-blue-950/40 text-white" : "text-slate-400 hover:bg-slate-800"}`}
                  >
                    <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition
                      ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                      {isSelected && (
                        <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    {s.title}
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3">
              {!wizardProfile.automationPrimary && (
                <button
                  onClick={() => setStep(9)}
                  className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
                >
                  {selectedProduct.shortName} odagiyla kurulumu tamamla →
                </button>
              )}
              <button
                onClick={goToMaviyaka}
                disabled={selectedIds.size === 0}
                className="flex items-center gap-2 rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-white transition hover:border-blue-500 hover:text-blue-300 disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:text-white"
              >
                🚀 Web otomasyonuna gec ({selectedIds.size} senaryo)
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 7: Otomasyon Kurulumu ── */}
        {step === 7 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">
                🚀 {projectName?.trim() || "Proje"} — Otomasyon Kurulumu
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Hedef URL, ortam ve lokator dosyalarını tanımla; AI Gherkin feature dosyalarını üretecek.
              </p>
            </div>
            {!wizardProfile.automationPrimary && (
              <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4 text-sm text-violet-100">
                Secili urun: <span className="font-semibold">{selectedProduct.name}</span>. Bu adim yardimci bir web otomasyon uzantisidir; kurulum bitsin diye zorunlu degil.
              </div>
            )}

            {/* URL + Domain */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-300">Hedef Uygulama</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">URL</label>
                  <input
                    value={maviyakaUrl}
                    onChange={(e) => setMaviyakaUrl(e.target.value)}
                    placeholder="https://app.example.com"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="wizard-environment" className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">Ortam</label>
                  <select
                    id="wizard-environment"
                    aria-label="Ortam"
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value as typeof environment)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
                  >
                    <option value="dev">DEV</option>
                    <option value="test">TEST</option>
                    <option value="qa">QA</option>
                    <option value="preprod">PREPROD</option>
                    <option value="prod">PROD</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Lokator Dosyaları */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-300">Lokator Dosyaları (JSON)</h3>
                <span className="text-xs text-slate-500">
                  {locatorFiles.reduce((a, f) => a + f.locators.length, 0)} lokator
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                  JSON Yükle (birden fazla)
                  <input type="file" accept=".json" multiple onChange={handleLocatorUpload} className="hidden" />
                </label>
                <span className="text-xs text-slate-600">veya</span>
                <button
                  type="button"
                  onClick={crawlLocators}
                  disabled={crawling || !maviyakaUrl.trim()}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-40"
                >
                  {crawling ? (
                    <>
                      <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Tarıyor…
                    </>
                  ) : "🕷 URL'yi Otomatik Tara"}
                </button>
              </div>

              {locatorFiles.length > 0 && (
                <div className="space-y-2">
                  {locatorFiles.map((lf, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveLocatorFile(lf)}
                      className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm transition
                        ${activeLocatorFile?.name === lf.name
                          ? "border-blue-500 bg-blue-950/20 text-blue-400"
                          : "border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500"}`}
                    >
                      <span>📋 {lf.name}</span>
                      <span className="text-xs text-slate-500">{lf.locators.length} lokator</span>
                    </button>
                  ))}
                </div>
              )}

              {activeLocatorFile && (
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 space-y-2 max-h-80 overflow-y-auto">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">
                    {activeLocatorFile.name}
                  </p>
                  {activeLocatorFile.locators.map((l, i) => {
                    const alts = l.alternatives || [];
                    return (
                      <div
                        key={i}
                        id={`locator-row-${l.key}`}
                        className="rounded-md border border-slate-800 bg-slate-900/60 p-2 transition-colors duration-700"
                      >
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-emerald-400 font-mono font-semibold">{l.key}</span>
                          {l.tag && (
                            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 font-mono">
                              {l.tag}
                            </span>
                          )}
                        </div>
                        <div className="mt-1 space-y-0.5">
                          <div className="flex items-start gap-2 text-xs">
                            <span className="rounded bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-mono text-blue-300 shrink-0">
                              {l.type}
                            </span>
                            <span className="text-slate-300 font-mono break-all">{l.value}</span>
                          </div>
                          {alts.map((alt, j) => (
                            <div key={j} className="flex items-start gap-2 text-xs">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-mono shrink-0 ${
                                  alt.type === "xpath"
                                    ? "bg-purple-500/15 text-purple-300"
                                    : "bg-slate-700/50 text-slate-400"
                                }`}
                              >
                                {alt.type}
                              </span>
                              <span className="text-slate-400 font-mono break-all">{alt.value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Manuel Test ⇄ Lokator Eşleşmesi */}
            {(matching || locatorMatches.length > 0) && (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-300">
                      🎯 Manuel Adım ⇄ Lokator Eşleşmeleri
                    </h3>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {matching
                        ? "Eşleştiriliyor…"
                        : `${locatorMatches.length} öneri · ${matchScenarioCount} senaryo incelendi — her satırda "Bu uygun mudur?" yanıtını ver.`}
                    </p>
                  </div>
                  {locatorMatches.length > 0 && !matching && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={approveAllMatches}
                        className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20"
                      >
                        ✓ Hepsini Onayla
                      </button>
                      <button
                        type="button"
                        onClick={rejectAllMatches}
                        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:border-slate-600"
                      >
                        ✗ Hepsini Reddet
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const all = locatorFiles.flatMap((f) => f.locators);
                          void matchLocatorsToScenarios(all);
                        }}
                        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:border-blue-500 hover:text-blue-300"
                      >
                        ↻ Tekrar Eşleştir
                      </button>
                    </div>
                  )}
                </div>

                {matching && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <svg className="h-4 w-4 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    AI senaryo adımlarını lokator önerileriyle karşılaştırıyor…
                  </div>
                )}

                {!matching && locatorMatches.length > 0 && matchLlmStatus && !matchLlmStatus.available && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                    <div className="flex items-center gap-2 font-semibold">
                      <span>⚠️</span>
                      <span>AI eşleştirme devre dışı — heuristic (anahtar kelime) fallback kullanılıyor</span>
                    </div>
                    <p className="mt-1 text-[11px] text-amber-300/80">
                      Güven skorları düşük (~%40–%60) ve tek tip görünebilir. LLM'i etkinleştirmek için backend'de
                      <code className="mx-1 rounded bg-amber-500/20 px-1 font-mono">OPENAI_API_KEY</code>
                      veya eşdeğer AI sağlayıcı ayarını kontrol edin.
                    </p>
                    {matchLlmStatus.error && (
                      <p className="mt-1 font-mono text-[10px] text-amber-300/60">
                        Hata: {matchLlmStatus.error}
                      </p>
                    )}
                  </div>
                )}

                {!matching && matchStats && matchStats.skipped_url_only > 0 && (
                  <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-400">
                    <span className="font-semibold text-slate-300">ℹ️ Bilgi:</span>{" "}
                    {matchStats.skipped_url_only} navigasyon adımı (URL'ye git, sayfa aç…) locator
                    eşleştirmesinden çıkarıldı. UI element referansı içermeyen adımlar için lokator
                    önerilmiyor.
                  </div>
                )}

                {!matching && unmatchedLocatorKeys.length > 0 && (
                  <details className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-400">
                    <summary className="cursor-pointer font-semibold text-slate-300">
                      🔍 {unmatchedLocatorKeys.length} lokator hiçbir adıma bağlanamadı — genişlet
                    </summary>
                    <p className="mt-1.5 text-[11px] text-slate-500">
                      Bu lokatörler crawl'da bulundu ama manuel senaryo adımlarınızdaki hiçbir
                      element ifadesiyle eşleşmedi. Muhtemelen bu elementleri kullanan adımı
                      unuttunuz veya locator key'leri adım metninden çok farklı isimlendirildi.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {unmatchedLocatorKeys.map((k) => (
                        <span
                          key={k}
                          className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300"
                        >
                          {k}
                        </span>
                      ))}
                    </div>
                  </details>
                )}

                {!matching && locatorMatches.length > 0 && (() => {
                  // Senaryo + adım bazlı grupla — her grup tek başlık, N candidate lokator
                  const groups = new Map<
                    string,
                    {
                      scenarioId: string;
                      scenarioTitle: string;
                      stepIdx: number;
                      stepText: string;
                      items: LocatorMatch[];
                    }
                  >();
                  for (const m of locatorMatches) {
                    const gk = `${m.scenario_id}::${m.step_index}`;
                    if (!groups.has(gk)) {
                      groups.set(gk, {
                        scenarioId: m.scenario_id,
                        scenarioTitle: m.scenario_title,
                        stepIdx: m.step_index,
                        stepText: m.step_text,
                        items: [],
                      });
                    }
                    groups.get(gk)!.items.push(m);
                  }

                  const xpathBadge = (q: LocatorMatch["xpath_quality"]) => {
                    if (!q) return null;
                    const palette: Record<string, { cls: string; icon: string; label: string }> = {
                      good:    { cls: "bg-emerald-500/15 text-emerald-300", icon: "🟢", label: "Stabil XPath" },
                      warn:    { cls: "bg-amber-500/15 text-amber-300",     icon: "🟡", label: "Kırılgan olabilir" },
                      bad:     { cls: "bg-red-500/15 text-red-300",         icon: "🔴", label: "Kırılgan XPath" },
                      invalid: { cls: "bg-red-700/30 text-red-200",         icon: "⛔", label: "Geçersiz XPath" },
                    };
                    const p = palette[q.grade] || palette.warn;
                    const tooltip = [
                      `${p.label} · skor %${q.score}`,
                      q.issues.length > 0 ? `Sorunlar: ${q.issues.join(", ")}` : null,
                      q.strengths.length > 0 ? `Güç: ${q.strengths.join(", ")}` : null,
                    ].filter(Boolean).join("\n");
                    return (
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${p.cls}`}
                        title={tooltip}
                      >
                        {p.icon} %{q.score}
                      </span>
                    );
                  };

                  const setGroupStatus = (items: LocatorMatch[], status: LocatorMatchStatus) => {
                    setMatchStatuses((prev) => {
                      const next = { ...prev };
                      items.forEach((m) => { next[matchKey(m)] = status; });
                      return next;
                    });
                  };

                  const groupList = Array.from(groups.values());
                  return (
                    <div className="space-y-3">
                      {groupList.map((grp) => {
                        const approvedCount = grp.items.filter((m) => matchStatuses[matchKey(m)] === "approved").length;
                        const rejectedCount = grp.items.filter((m) => matchStatuses[matchKey(m)] === "rejected").length;
                        const pendingCount = grp.items.length - approvedCount - rejectedCount;
                        return (
                          <div
                            key={`${grp.scenarioId}::${grp.stepIdx}`}
                            className="rounded-lg border border-slate-800 bg-slate-950/40"
                          >
                            {/* Grup başlığı */}
                            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 px-3 py-2">
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2 text-xs">
                                  <span className="text-slate-500">Senaryo:</span>
                                  <span className="text-slate-200 font-medium">{grp.scenarioTitle}</span>
                                  <span className="text-slate-600">·</span>
                                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] text-slate-300">
                                    Adım #{grp.stepIdx + 1}
                                  </span>
                                  <span className="text-slate-600">·</span>
                                  <span className="text-[11px] text-slate-500">
                                    {grp.items.length} lokator önerisi
                                  </span>
                                </div>
                                <p className="mt-1 text-xs text-slate-400">
                                  <span className="text-slate-600">Adım metni:</span> {grp.stepText}
                                </p>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                <span className="text-[11px] text-emerald-400">✓{approvedCount}</span>
                                <span className="text-[11px] text-slate-500">✗{rejectedCount}</span>
                                <span className="text-[11px] text-slate-600">·{pendingCount}</span>
                                {pendingCount > 0 && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => setGroupStatus(grp.items, "approved")}
                                      className="ml-1 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300 hover:bg-emerald-500/20"
                                      title="Bu adımdaki tüm önerileri onayla"
                                    >
                                      ✓ Adım
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setGroupStatus(grp.items, "rejected")}
                                      className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400 hover:border-slate-600"
                                      title="Bu adımdaki tüm önerileri reddet"
                                    >
                                      ✗ Adım
                                    </button>
                                  </>
                                )}
                              </div>
                            </div>

                            {/* Aday lokator satırları */}
                            <div className="divide-y divide-slate-800/60">
                              {grp.items.map((m) => {
                                const mk = matchKey(m);
                                const status = matchStatuses[mk] || "pending";
                                const rowCls =
                                  status === "approved"
                                    ? "bg-emerald-500/5"
                                    : status === "rejected"
                                    ? "opacity-50"
                                    : "";
                                const confPct = Math.round((m.confidence || 0) * 100);
                                const confColor =
                                  confPct >= 80 ? "text-emerald-400" : confPct >= 60 ? "text-amber-400" : "text-red-400";
                                const sourceBadge: Record<string, { cls: string; icon: string; title: string }> = {
                                  llm:       { cls: "bg-sky-500/15 text-sky-300",       icon: "🤖", title: "AI semantik eşleştirme" },
                                  heuristic: { cls: "bg-amber-500/15 text-amber-300",   icon: "📐", title: "Heuristic — anahtar kelime örtüşmesi (AI devre dışı)" },
                                  manual:    { cls: "bg-emerald-500/15 text-emerald-300", icon: "👤", title: "Kullanıcı tarafından manuel seçildi" },
                                };
                                const sb = sourceBadge[m.source || "heuristic"] || sourceBadge.heuristic;
                                // Bu adımdaki diğer öneriler — aynı key iki kez listelenmesin
                                const otherKeysForStep = grp.items.map((im) => im.suggested_key);
                                const availableKeys = locatorFiles
                                  .flatMap((f) => f.locators.map((l) => l.key))
                                  .filter((k) => !otherKeysForStep.includes(k));
                                return (
                                  <div key={mk} className={`relative px-3 py-2 transition ${rowCls}`}>
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="min-w-0 flex-1">
                                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                                          <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                                            {m.element_phrase || "—"}
                                          </span>
                                          <span className="text-slate-600">→</span>
                                          <button
                                            type="button"
                                            onClick={() => jumpToLocator(m.suggested_key)}
                                            className="rounded bg-blue-500/15 px-2 py-0.5 font-mono text-blue-300 hover:bg-blue-500/25 hover:underline"
                                            title="Locator editöründe aç"
                                          >
                                            {m.suggested_key}
                                          </button>
                                          <span
                                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${sb.cls}`}
                                            title={sb.title}
                                          >
                                            {sb.icon}
                                          </span>
                                          {xpathBadge(m.xpath_quality)}
                                          <span className={`ml-auto font-mono text-[11px] ${confColor}`}>
                                            %{confPct}
                                          </span>
                                        </div>
                                        <div className="mt-1 font-mono text-[11px] text-slate-500 break-all">
                                          {m.suggested_locator.type}={m.suggested_locator.value}
                                        </div>
                                        {m.reason && (
                                          <p className="mt-0.5 text-[11px] text-slate-600 italic">{m.reason}</p>
                                        )}
                                      </div>
                                      <div className="flex flex-col gap-1 shrink-0">
                                        <button
                                          type="button"
                                          onClick={() => setMatchStatus(mk, "approved")}
                                          aria-label={`${m.suggested_key} önerisini onayla`}
                                          className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                            status === "approved"
                                              ? "bg-emerald-500 text-white"
                                              : "border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                                          }`}
                                        >
                                          ✓
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setOverridePopoverKey((prev) => (prev === mk ? null : mk))
                                          }
                                          aria-label={`${m.suggested_key} için başka locator seç`}
                                          className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                            overridePopoverKey === mk
                                              ? "bg-blue-500 text-white"
                                              : "border border-slate-700 bg-slate-800 text-slate-400 hover:border-blue-500 hover:text-blue-300"
                                          }`}
                                          title="Başka locator seç"
                                        >
                                          ↻
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() => setMatchStatus(mk, "rejected")}
                                          aria-label={`${m.suggested_key} önerisini reddet`}
                                          className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                            status === "rejected"
                                              ? "bg-slate-600 text-white"
                                              : "border border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
                                          }`}
                                        >
                                          ✗
                                        </button>
                                      </div>
                                    </div>
                                    {overridePopoverKey === mk && (
                                      <div className="mt-2 rounded-lg border border-blue-500/30 bg-slate-950 p-2">
                                        <div className="mb-1.5 flex items-center justify-between text-[11px]">
                                          <span className="font-semibold text-blue-300">
                                            Bu adıma başka bir locator ata
                                          </span>
                                          <button
                                            type="button"
                                            onClick={() => setOverridePopoverKey(null)}
                                            className="text-slate-500 hover:text-slate-300"
                                          >
                                            ✕
                                          </button>
                                        </div>
                                        {availableKeys.length === 0 ? (
                                          <p className="text-[11px] text-slate-500">
                                            Bu adımdaki diğer öneriler dışında locator kalmadı.
                                          </p>
                                        ) : (
                                          <div className="max-h-32 overflow-y-auto space-y-0.5">
                                            {availableKeys.map((k) => (
                                              <button
                                                key={k}
                                                type="button"
                                                onClick={() => overrideMatchLocator(mk, k)}
                                                className="w-full rounded px-2 py-1 text-left font-mono text-[11px] text-slate-300 hover:bg-blue-500/15 hover:text-blue-300"
                                              >
                                                {k}
                                              </button>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}

                      <div className="flex flex-wrap items-center gap-4 border-t border-slate-800 pt-3 text-xs">
                        <span className="text-slate-500">
                          {groupList.length} adım · {locatorMatches.length} öneri
                        </span>
                        <span className="text-emerald-400">
                          ✓ {Object.values(matchStatuses).filter((s) => s === "approved").length} onaylı
                        </span>
                        <span className="text-slate-500">
                          ✗ {Object.values(matchStatuses).filter((s) => s === "rejected").length} reddedildi
                        </span>
                        <span className="text-slate-600">
                          {Object.values(matchStatuses).filter((s) => s === "pending").length} bekleniyor
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Feature Üret + Manuel Senaryo Eşleştirme Butonları */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={generateMaviyakaFeatures}
                disabled={loading || matchingFull || !maviyakaUrl.trim()}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Üretiliyor…
                  </>
                ) : "🤖 Feature Dosyaları Üret"}
              </button>
              <button
                type="button"
                onClick={matchAndGenerateFromManual}
                disabled={matchingFull || loading || !maviyakaUrl.trim()}
                title="Mevcut manuel senaryoların her adımını locator kataloğundaki key + XPath ile LLM üzerinden eşler. Sonuç: feature + adım→XPath raporu."
                className="flex items-center gap-2 rounded-xl border border-purple-500/50 bg-purple-600/20 px-6 py-2.5 text-sm font-semibold text-purple-200 transition hover:bg-purple-600/30 disabled:opacity-40"
              >
                {matchingFull ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Eşleştiriliyor…
                  </>
                ) : "🔗 Mevcut Manuel Senaryolarla Eşleştir"}
              </button>
              {stepMappings.length > 0 && (
                <span className="text-xs text-slate-500">
                  {stepMappings.length} senaryo · {stepMappings.reduce((a, m) => a + m.steps.length, 0)} adım bağlandı
                </span>
              )}
            </div>

            {/* Feature Dosyaları + Syntax Highlight */}
            {maviyakaFeatures.length > 0 && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-4">
                  <h3 className="text-sm font-semibold text-slate-300">Üretilen Feature Dosyaları</h3>
                  <span className="text-[11px] text-slate-500">
                    <span className="text-blue-400 font-semibold">keyword</span>
                    &nbsp;·&nbsp;
                    <span className="text-emerald-400">mevcut lokator</span>
                    &nbsp;·&nbsp;
                    <span className="text-red-400 underline">eksik lokator (tıkla → AI)</span>
                  </span>
                </div>

                {/* Sekme seçici */}
                <div className="flex flex-wrap gap-1.5">
                  {maviyakaFeatures.map((f, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveFeatureIdx(i)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition
                        ${activeFeatureIdx === i ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
                    >
                      {f.title}
                    </button>
                  ))}
                </div>

                {maviyakaFeatures[activeFeatureIdx] && (
                  <MaviyakaFeatureViewer
                    content={maviyakaFeatures[activeFeatureIdx].content}
                    allLocators={locatorFiles.flatMap((f) => f.locators)}
                    onRedKeyClick={suggestLocatorForKey}
                  />
                )}

                {/* LLM Destekli Adım → Locator → XPath Raporu */}
                {stepMappings.length > 0 && (
                  <div className="rounded-xl border border-purple-500/30 bg-slate-900 p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-purple-200">
                          🔗 Adım → Locator → XPath Eşleme Raporu
                        </h3>
                        <p className="mt-0.5 text-xs text-slate-500">
                          LLM her manuel adımı katalogdaki bir key ile eşledi ve karşılığındaki XPath değerini feature&apos;a gömdü.
                          Kırmızı satırlar: locator gerekli ama bulunamadı → satırdaki <span className="font-semibold text-amber-300">AI öner</span> ile hızlıca yeni locator öner.
                          <span className="ml-1 text-slate-400">open</span> gibi URL tabanlı aksiyonlar için locator gerekmez.
                        </p>
                        <p className="mt-1 text-[11px] text-slate-500">
                          Her XPath'in yanında <span className="text-emerald-300">sağlam</span> /
                          <span className="mx-1 text-amber-300">orta</span> /
                          <span className="text-red-300">kırılgan</span> rozeti var
                          (absolute path, numeric index, dinamik class gibi kırılganlıkları otomatik işaretler).
                          Üzerine gelince nedenleri görürsün.
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-[11px]">
                        <span className="rounded bg-purple-500/15 px-2 py-0.5 text-purple-300">LLM</span>
                        <span className="rounded bg-blue-500/15 px-2 py-0.5 text-blue-300">Kural</span>
                        <span className="rounded bg-slate-700 px-2 py-0.5 text-slate-300">Otomatik</span>
                      </div>
                    </div>

                    {/* Senaryo sekmeleri */}
                    <div className="flex flex-wrap gap-1.5">
                      {stepMappings.map((m, i) => {
                        const missing = m.steps.filter(
                          (s) => s.idx >= 0 && actionNeedsLocator(s.action) && !s.locator_key,
                        ).length;
                        return (
                          <button
                            key={m.scenario_id || i}
                            type="button"
                            onClick={() => setActiveMappingIdx(i)}
                            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition
                              ${activeMappingIdx === i
                                ? "bg-purple-600 text-white"
                                : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
                          >
                            <span className="max-w-[240px] truncate">{m.scenario_title}</span>
                            {missing > 0 && (
                              <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] text-red-300">
                                {missing} eksik
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {stepMappings[activeMappingIdx] && (
                      <div className="overflow-hidden rounded-lg border border-slate-800">
                        <table className="w-full text-xs">
                          <thead className="bg-slate-950 text-[10px] uppercase tracking-widest text-slate-500">
                            <tr>
                              <th className="px-3 py-2 text-left w-[28%]">Adım</th>
                              <th className="px-3 py-2 text-left w-[10%]">Aksiyon</th>
                              <th className="px-3 py-2 text-left w-[18%]">Locator Key</th>
                              <th className="px-3 py-2 text-left w-[30%]">XPath</th>
                              <th className="px-3 py-2 text-left w-[14%]">Kaynak</th>
                            </tr>
                          </thead>
                          <tbody>
                            {stepMappings[activeMappingIdx].steps.map((s, si) => {
                              const needsLoc = actionNeedsLocator(s.action);
                              const missing = s.idx >= 0 && needsLoc && !s.locator_key;
                              const rowCls = missing
                                ? "bg-red-950/30 border-t border-red-900/30"
                                : "border-t border-slate-800 hover:bg-slate-800/30";
                              const sourceBadge =
                                s.source === "llm"
                                  ? "bg-purple-500/15 text-purple-300"
                                  : s.source === "rule"
                                  ? "bg-blue-500/15 text-blue-300"
                                  : "bg-slate-700 text-slate-300";
                              const actionColor =
                                s.action === "click"
                                  ? "text-amber-300"
                                  : s.action === "input"
                                  ? "text-sky-300"
                                  : s.action === "see" || s.action === "verify"
                                  ? "text-emerald-300"
                                  : "text-slate-300";
                              return (
                                <tr key={si} className={rowCls}>
                                  <td className="px-3 py-2 text-slate-300">
                                    <div className="flex items-start gap-2">
                                      <span className="shrink-0 text-slate-600 font-mono">
                                        {s.idx >= 0 ? `#${s.idx + 1}` : "auto"}
                                      </span>
                                      <span className="break-words">{s.original}</span>
                                    </div>
                                    {s.data_value && (
                                      <div className="mt-1 text-[10px] text-yellow-400 font-mono">
                                        data: &quot;{s.data_value}&quot;
                                      </div>
                                    )}
                                  </td>
                                  <td className="px-3 py-2">
                                    <span className={`font-mono ${actionColor}`}>{s.action}</span>
                                  </td>
                                  <td className="px-3 py-2">
                                    {s.locator_key ? (
                                      <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-emerald-300">
                                        {s.locator_key}
                                      </span>
                                    ) : !needsLoc ? (
                                      <span
                                        className="rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400"
                                        title="Bu aksiyon element gerektirmez (ör. open → URL tabanlı)"
                                      >
                                        locator gerekmez
                                      </span>
                                    ) : (
                                      <div className="flex flex-wrap items-center gap-1.5">
                                        <span className="text-red-400 italic">eksik</span>
                                        <button
                                          type="button"
                                          onClick={() => suggestLocatorForStep(s)}
                                          className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300 transition hover:bg-amber-500/20"
                                          title="Bu adım için AI'dan yeni locator önerisi al"
                                        >
                                          AI öner
                                        </button>
                                      </div>
                                    )}
                                    {typeof s.score === "number" && s.source === "rule" && (
                                      <span className="ml-1.5 text-[10px] text-slate-500">%{Math.round((s.score || 0) * 100)}</span>
                                    )}
                                  </td>
                                  <td className="px-3 py-2">
                                    {s.xpath ? (
                                      <div className="space-y-1">
                                        <div className="flex items-start gap-1.5">
                                          <code className="break-all text-[11px] text-slate-400 flex-1">{s.xpath}</code>
                                          <button
                                            type="button"
                                            onClick={() => {
                                              navigator.clipboard?.writeText(s.xpath || "");
                                              notify("XPath kopyalandı");
                                            }}
                                            className="shrink-0 rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 hover:bg-slate-700 hover:text-white"
                                            title="XPath'i kopyala"
                                          >
                                            kopya
                                          </button>
                                        </div>
                                        {s.xpath_quality && (
                                          (() => {
                                            const q = s.xpath_quality!;
                                            const cls =
                                              q.grade === "good"
                                                ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                                                : q.grade === "warn"
                                                ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
                                                : q.grade === "bad"
                                                ? "bg-red-500/15 text-red-300 border-red-500/40"
                                                : "bg-slate-700/40 text-slate-400 border-slate-600";
                                            const label =
                                              q.grade === "good" ? "sağlam"
                                              : q.grade === "warn" ? "orta"
                                              : q.grade === "bad" ? "kırılgan"
                                              : "geçersiz";
                                            const tip = [
                                              q.strengths.length > 0 ? `✓ ${q.strengths.join(", ")}` : "",
                                              q.issues.length > 0 ? `⚠ ${q.issues.join(", ")}` : "",
                                            ].filter(Boolean).join("  |  ");
                                            return (
                                              <div
                                                className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10px] ${cls}`}
                                                title={tip || "XPath kalite skoru"}
                                              >
                                                <span className="font-semibold">{q.score}</span>
                                                <span className="opacity-80">{label}</span>
                                                {q.issues.length > 0 && (
                                                  <span className="opacity-70">· {q.issues[0]}{q.issues.length > 1 ? ` +${q.issues.length - 1}` : ""}</span>
                                                )}
                                              </div>
                                            );
                                          })()
                                        )}
                                      </div>
                                    ) : !needsLoc ? (
                                      <span className="text-[11px] italic text-slate-500">URL tabanlı aksiyon</span>
                                    ) : (
                                      <span className="text-slate-600">—</span>
                                    )}
                                  </td>
                                  <td className="px-3 py-2">
                                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${sourceBadge}`}>
                                      {s.source}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* AI Test Verisi */}
                {Object.keys(testDataMap).length > 0 && (
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
                      AI Üretilen Test Verisi
                    </p>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {Object.entries(testDataMap).map(([k, v]) => (
                        <div key={k} className="rounded-lg bg-slate-950 px-3 py-2 text-xs">
                          <span className="text-yellow-400 font-mono">@{k}</span>
                          <span className="text-slate-600 mx-1">=</span>
                          <span className="text-slate-300">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Başlat / Atla */}
                <div className="flex flex-wrap gap-3 pt-2">
                  <button
                    type="button"
                    onClick={openIdeForRun}
                    disabled={running || ideRunning}
                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
                  >
                    💻 Testleri Başlat — IDE&apos;de aç
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(9)}
                    className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                  >
                    Atla & Bitir →
                  </button>
                </div>
              </div>
            )}

            {/* Geri butonu (feature üretilmediyse) */}
            {maviyakaFeatures.length === 0 && (
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setStep(6)}
                  className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                >
                  ← Geri
                </button>
                <button
                  type="button"
                  onClick={() => setStep(9)}
                  className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                >
                  Atla →
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 8: Otomasyon IDE ── */}
        {step === 8 && (
          <IdeWorkbench
            projectName={projectName}
            projectSlug={projectSlug}
            environment={environment}
            ideFiles={ideFiles}
            activeIdePath={activeIdePath}
            setActiveIdePath={setActiveIdePath}
            setIdeFiles={setIdeFiles}
            expandedFolders={expandedFolders}
            toggleFolder={toggleFolder}
            consoleLines={consoleLines}
            ideTab={ideTab}
            setIdeTab={setIdeTab}
            ideRunning={ideRunning}
            runFromIde={runFromIde}
            stopFromIde={stopFromIde}
            goBack={() => setStep(7)}
            goFinish={() => setStep(9)}
          />
        )}

        {/* ── STEP 9: Tamamlandı ── */}
        {step === 9 && (
          <div className="space-y-5">
            <div>
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600/20">
                <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-bold">Proje Hazır!</h2>
              <p className="mt-1 text-sm text-slate-400">
                {featureFiles.length + testFiles.length > 0
                  ? `${featureFiles.length} feature + ${testFiles.length} test dosyası üretildi. Dosyaları incele ve projeye git.`
                  : "Otomasyon kodu üretildi. Dosyaları incele ve projeye git."}
              </p>
            </div>

            <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200/80">Hazir acilis noktasi</p>
                  <p className="mt-2 text-lg font-semibold text-white">{selectedProduct.name}</p>
                  <p className="mt-1 text-sm text-slate-300">{productGuide.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{productGuide.description}</p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
                  {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
                </span>
              </div>
            </div>

            {/* Dosya yoksa yeniden üret */}
            {featureFiles.length === 0 && testFiles.length === 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center space-y-3">
                <p className="text-sm text-slate-400">
                  Dosyalar yüklenemedi. Tekrar denemek için aşağıdaki butonu kullanın.
                </p>
                <button
                  onClick={() => setStep(6)}
                  className="rounded-xl border border-slate-700 px-5 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
                >
                  ← Otomasyon adımına dön
                </button>
              </div>
            )}

            {/* Dosya gezgini */}
            {(featureFiles.length > 0 || testFiles.length > 0) && (
            <div className="flex gap-4 rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden" style={{ minHeight: 400 }}>
              {/* Sol panel — dosya listesi */}
              <div className="w-56 shrink-0 border-r border-slate-800 p-3 space-y-1">
                {featureFiles.length > 0 && (
                  <>
                    <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Feature Dosyaları</p>
                    {featureFiles.map((f, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveFile(f)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                          ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                      >
                        📄 {f.name}
                      </button>
                    ))}
                  </>
                )}
                {testFiles.length > 0 && (
                  <>
                    <p className="mt-3 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Test Dosyaları</p>
                    {testFiles.map((f, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveFile(f)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                          ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                      >
                        🧪 {f.name}
                      </button>
                    ))}
                  </>
                )}
              </div>

              {/* Sağ panel — kod görüntüleyici */}
              <div className="flex-1 overflow-auto p-4">
                {activeFile ? (
                  <>
                    <p className="mb-3 text-xs font-medium text-slate-500">{activeFile.name}</p>
                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                      {activeFile.content}
                    </pre>
                  </>
                ) : (
                  <p className="text-sm text-slate-600 mt-4">Sol panelden bir dosya seç</p>
                )}
              </div>
            </div>
            )}

            {/* Çalıştırma çıktısı */}
            {runOutput && (
              <div className="rounded-xl border border-emerald-800 bg-emerald-950/30 p-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-400">Test Sonucu</p>
                <pre className="text-xs text-emerald-300 whitespace-pre-wrap">{runOutput}</pre>
              </div>
            )}

            {/* CTA butonları */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => router.push(projectEntryHref(projectId, selectedProduct.id))}
                className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
              >
                {selectedProduct.shortName} çalışma alanini ac →
              </button>
              <button
                onClick={() => router.push(`/p/${projectId}`)}
                className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                Proje Özetine git
              </button>
              <button
                onClick={() => router.push(`/p/${projectId}/${productGuide.recommendedPath}`)}
                className="rounded-xl border border-violet-500/20 bg-violet-500/10 px-6 py-2.5 text-sm font-medium text-violet-100 transition hover:border-violet-400/30 hover:bg-violet-500/15"
              >
                Önerilen adım: {selectedProduct.shortName}
              </button>
              <button
                onClick={() => router.push("/")}
                className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
              >
                Ana Sayfa
              </button>
            </div>
          </div>
        )}
          </div>

          {/* Sağ sticky context paneli (xl+) */}
          <aside className="hidden xl:block">
            <div className="sticky top-6 space-y-4">
              {/* Aktif ürün kartı */}
              <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-violet-200/80">
                  Product Focus
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <h3 className="text-base font-semibold text-white">{selectedProduct.name}</h3>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
                    {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
                  </span>
                </div>
                <p className="mt-1 text-xs text-violet-200/90">{selectedProduct.tagline}</p>
                <p className="mt-3 text-xs leading-5 text-slate-400">{productGuide.description}</p>
                <p className="mt-3 rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-2 text-[11px] leading-5 text-slate-400">
                  Wizard sonunda önce{" "}
                  <span className="font-semibold text-slate-200">{selectedProduct.shortName}</span>{" "}
                  yüzeyine indireceğim.
                </p>
              </div>

              {/* Ürün değiştirici */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Ürünü değiştir
                </p>
                <div className="mt-3 grid grid-cols-2 gap-1.5">
                  {PRODUCT_FAMILY.map((product) => (
                    <button
                      key={product.id}
                      type="button"
                      onClick={() => applyProduct(product.id)}
                      className={`rounded-lg border px-2 py-1.5 text-left transition ${
                        product.id === selectedProduct.id
                          ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                          : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                      }`}
                    >
                      <span className="block text-[9px] font-semibold uppercase tracking-[0.14em]">
                        {product.shortName}
                      </span>
                      <span className="mt-0.5 block text-[10px] leading-tight">{product.tagline}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Bu adımda kartı */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Bu adımda
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
                  <span className="text-base">{STEPS[step - 1]?.icon}</span>
                  {STEPS[step - 1]?.label}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  {STEPS[step - 1]?.desc}
                </p>
                <div className="mt-3 border-t border-slate-800 pt-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Odak akışı
                  </p>
                  <p className="mt-1.5 text-xs font-medium text-slate-200">{productGuide.title}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {selectedProduct.routeSegments.slice(0, 4).map((segment) => (
                      <span
                        key={segment}
                        className="rounded-full border border-slate-700 bg-slate-950 px-1.5 py-0.5 text-[9px] font-medium text-slate-400"
                      >
                        {segment}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* ── Lokator Modal ── */}
      {locatorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-semibold text-white">🤖 AI Lokator Önerisi</h3>
              <p className="mt-1 text-sm text-slate-400">
                <span className="text-red-400 font-mono">&quot;{locatorModal.key}&quot;</span> için AI önerisi:
              </p>
            </div>

            {locatorModal.aiSuggestion === null ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI lokator arıyor…
              </div>
            ) : (
              <pre className="rounded-lg bg-slate-950 p-3 text-xs text-emerald-400 font-mono overflow-auto max-h-48">
                {locatorModal.aiSuggestion}
              </pre>
            )}

            <div className="flex gap-3">
              {locatorModal.aiSuggestion !== null && (() => {
                let entry: LocatorEntry | null = null;
                try { entry = JSON.parse(locatorModal.aiSuggestion); } catch { /* */ }
                return entry ? (
                  <button
                    type="button"
                    onClick={() => confirmLocator(entry!)}
                    className="flex-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
                  >
                    ✓ Onayla & Kaydet
                  </button>
                ) : null;
              })()}
              <button
                type="button"
                onClick={() => setLocatorModal(null)}
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-400 transition hover:border-slate-500 hover:text-white"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
