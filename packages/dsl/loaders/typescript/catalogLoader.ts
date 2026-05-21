/**
 * BGTS DSL TypeScript Loader (cucumber-js için)
 *
 * packages/dsl/catalog/*.yaml dosyalarını okuyup her alias için
 * cucumber-js Given/When/Then step kaydı yapar. Her alias aynı
 * implementation fonksiyonuna resolve olur — böylece tek bir yerde
 * implementation yazılır, TR/EN/birden çok varyant aynı koda bağlanır.
 *
 * Kullanım (cucumber.js içinde require'dan önce veya steps/hooks.ts içinde):
 *
 *   import { registerCatalog } from '../../../packages/dsl/loaders/typescript/catalogLoader';
 *   registerCatalog({ onlyCategories: ['ui'] });
 *
 * Implementation fonksiyonlarının nasıl bulunacağı:
 *   - catalog YAML'de implementations.typescript.module = "web-steps" gibi
 *     göreli modül adı verilirse dynamic require edilir
 *   - Alternatif: implementations.typescript.function_ref ile global/
 *     registry üzerinden callback verilir (pilot migration için)
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';

// cucumber-js runtime'da çağıran dosyanın node_modules'undan resolve edilir.
// Bu sayede loader'ı farklı projelerden import edebiliriz.
type StepFn = (pattern: string, fn: (...args: any[]) => any) => void;

function loadCucumber(): { Given: StepFn; When: StepFn; Then: StepFn } | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod = require('@cucumber/cucumber');
    return { Given: mod.Given, When: mod.When, Then: mod.Then };
  } catch {
    return null;
  }
}

// ── Tipler ───────────────────────────────────────────────────────────
interface YamlImplementation {
  source_file?: string;
  module?: string;
  function?: string;
  class?: string;
  method?: string;
  pattern?: string;
  function_ref?: string; // registry key
}

interface YamlAction {
  id: string;
  category: string;
  description?: string;
  aliases?: Record<string, string[]>;
  parameters?: Array<{ name: string; type?: string; required?: boolean }>;
  implementations?: Record<string, YamlImplementation>;
  tags?: string[];
  deprecated?: boolean | { replacement?: string };
}

export interface CatalogBinding {
  id: string;
  category: string;
  keyword: 'given' | 'when' | 'then';
  aliasesRegistered: string[];
  implRef?: string;
  skippedReason?: string;
}

export interface RegisterOptions {
  catalogDir?: string;
  onlyCategories?: string[];
  skipIds?: string[];
  dryRun?: boolean;
  /**
   * Global fonksiyon registry. implementations.typescript.function_ref bu map'te
   * bulunursa fonksiyon olarak kullanılır. Pilot migration'da kullanılır.
   */
  registry?: Record<string, (...args: any[]) => any>;
  /** Base dir where implementations.source_file paths are resolved */
  projectRoot?: string;
}

// ── Yardımcılar ──────────────────────────────────────────────────────

function defaultCatalogDir(): string {
  return path.resolve(__dirname, '..', '..', 'catalog');
}

function detectKeyword(tags: string[] = []): 'given' | 'when' | 'then' {
  for (const kw of ['given', 'when', 'then'] as const) {
    if (tags.includes(kw)) return kw;
  }
  return 'when';
}

function loadCatalog(dir: string): YamlAction[] {
  if (!fs.existsSync(dir)) {
    console.warn(`[DSL] Katalog dizini yok: ${dir}`);
    return [];
  }
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.yaml')).sort();
  const actions: YamlAction[] = [];
  for (const f of files) {
    const full = path.join(dir, f);
    try {
      const raw = fs.readFileSync(full, 'utf-8');
      const doc = yaml.load(raw) as { actions?: YamlAction[] } | undefined;
      if (!doc || !Array.isArray(doc.actions)) continue;
      for (const a of doc.actions) {
        if (a && typeof a === 'object' && typeof a.id === 'string') {
          actions.push(a);
        }
      }
    } catch (err) {
      console.warn(`[DSL] ${f} parse hatası: ${(err as Error).message}`);
    }
  }
  return actions;
}

function resolveImpl(
  impl: YamlImplementation,
  registry: Record<string, (...args: any[]) => any>,
  projectRoot: string,
): ((...args: any[]) => any) | null {
  // 1) registry öncelikli (pilot migration)
  if (impl.function_ref && registry[impl.function_ref]) {
    return registry[impl.function_ref];
  }

  // 2) implementations.typescript.module ile dinamik require (steps/web-steps gibi)
  if (impl.module && impl.function) {
    try {
      // cucumber-js steps/ klasörüne göre çözümlenir; steps altında çalışır
      const mod = require(impl.module);
      const fn = mod[impl.function] ?? mod.default?.[impl.function];
      if (typeof fn === 'function') return fn;
    } catch {
      /* yoksay */
    }
  }

  // 3) source_file + function (frameworks/playwright-cucumber-ts/steps/web-steps.ts)
  if (impl.source_file && impl.function) {
    try {
      const fullPath = path.resolve(projectRoot, impl.source_file.replace(/\.ts$/, ''));
      const mod = require(fullPath);
      const fn = mod[impl.function] ?? mod.default?.[impl.function];
      if (typeof fn === 'function') return fn;
    } catch {
      /* yoksay */
    }
  }

  return null;
}

// ── Ana API ──────────────────────────────────────────────────────────

export function loadActions(options: RegisterOptions = {}): YamlAction[] {
  const dir = options.catalogDir ?? defaultCatalogDir();
  return loadCatalog(dir);
}

export function registerCatalog(options: RegisterOptions = {}): CatalogBinding[] {
  const {
    onlyCategories,
    skipIds = [],
    dryRun = false,
    registry = {},
    projectRoot = path.resolve(__dirname, '..', '..', '..', '..'),
  } = options;

  const actions = loadActions(options);
  const bindings: CatalogBinding[] = [];
  const cucumber = dryRun ? null : loadCucumber();
  if (!dryRun && !cucumber) {
    console.warn('[DSL] @cucumber/cucumber yüklü değil; sadece dry-run yapılabilir.');
    options.dryRun = true;
  }
  const keywordMap = cucumber
    ? ({ given: cucumber.Given, when: cucumber.When, then: cucumber.Then } as const)
    : null;
  const skipSet = new Set(skipIds);

  for (const action of actions) {
    const topCat = (action.category || '').split('.')[0];
    const binding: CatalogBinding = {
      id: action.id,
      category: action.category,
      keyword: detectKeyword(action.tags ?? []),
      aliasesRegistered: [],
    };

    if (skipSet.has(action.id)) {
      binding.skippedReason = 'skip_ids';
      bindings.push(binding);
      continue;
    }
    if (onlyCategories && !onlyCategories.includes(topCat)) {
      binding.skippedReason = 'not in onlyCategories';
      bindings.push(binding);
      continue;
    }

    const tsImpl = action.implementations?.typescript;
    if (!tsImpl) {
      binding.skippedReason = 'no typescript implementation';
      bindings.push(binding);
      continue;
    }

    binding.implRef = tsImpl.function_ref
      ?? `${tsImpl.module ?? tsImpl.source_file}.${tsImpl.function ?? '?'}`;

    const fn = dryRun ? null : resolveImpl(tsImpl, registry, projectRoot);
    if (!dryRun && !fn) {
      binding.skippedReason = 'impl not resolvable';
      bindings.push(binding);
      continue;
    }

    const aliases = action.aliases ?? {};
    const allAliases: string[] = [];
    for (const arr of Object.values(aliases)) {
      if (Array.isArray(arr)) allAliases.push(...arr);
    }
    if (allAliases.length === 0) {
      binding.skippedReason = 'no aliases';
      bindings.push(binding);
      continue;
    }

    const register = keywordMap ? keywordMap[binding.keyword] : null;
    for (const alias of allAliases) {
      if (dryRun || !register) {
        binding.aliasesRegistered.push(alias);
        continue;
      }
      try {
        register(alias, fn as any);
        binding.aliasesRegistered.push(alias);
      } catch (err) {
        console.warn(`[DSL] alias kaydedilemedi ${action.id} -> ${alias}: ${(err as Error).message}`);
      }
    }

    bindings.push(binding);
  }

  const active = bindings.filter((b) => !b.skippedReason);
  const registered = active.reduce((s, b) => s + b.aliasesRegistered.length, 0);
  console.info(
    `[DSL] ${registered} alias kaydedildi (${active.length} cümlecik aktif, ${bindings.length - active.length} atlandı)`,
  );
  return bindings;
}
