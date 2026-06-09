# Cortex AI Frontend Refactor — FAZA 0 Sprint Plan (3 Hafta)

## Özet
- **Dönem:** 3 hafta (18 güngün)
- **Amaç:** 4 kritik + 5 blocking yüksek-risk bulgu fix
- **Ekip:** 3-4 developer, 1 designer, 1 QA
- **Başarı:** 0 TypeScript error, Lighthouse ≥80, Bundle <500KB, 0 linter violation
- **Risk:** Mega-component split'ler, query key consistency, responsive refactor

---

## KRİTİK BULGULAR (4)

| # | Dosya | Satır | Problem | Çözüm | Efor |
|---|-------|-------|---------|-------|------|
| 1 | `apps/web/app/new-project/page.tsx` | 2835 | Mega-component: Wizard + Form + Submit + API logic karışık | Split → _components/(Wizard, FormFields, Summary, useProjectForm) | 4-5 gün |
| 2 | `apps/web/lib/hooks/use-management.ts` | 2604 | Monolitik hook: bundle bloat, 12 domain karışık | Domain-driven split → 6 hook dosyası (test, case, defect, etc.) | 6-8 gün |
| 3 | `apps/web/components/AppShell.tsx` | 882 | State + presentational karışımı: 5 useState, 8 useEffect | Extract → _components/(SidebarNav, ProductPicker, UserMenu, LayoutFrame) | 4-5 gün |
| 4 | Type definitions (contracts) | — | AI Provider, Config, TaskType inconsistent types | @neurex/contracts schema (Zod) + TypeScript codegen | 2-3 gün |

## BLOCKING BULGULAR (5)

| # | Dosya | Problem | Çözüm | Efor |
|---|-------|---------|-------|------|
| 5 | `lib/query-keys.ts` + 50 hook | Query key inconsistency (string vs factory, naming) | Centralize factory + audit 50 hook | 3 gün |
| 6 | 40+ `.ts/.tsx` dosya | TypeScript ~40 error (type mismatch, implicit any) | tsc --strict audit + fix cascade | 3 gün |
| 7 | 50+ component | Tier undefined (container vs presentational vs smart) | ADR-0015: tier classification + linter rule | 2 gün |
| 8 | 20+ form | Form validation scattered (Zod vs manual vs none) | Standardize → Zod schema factory | 3 gün |
| 9 | 28 E2E spec | Critical path untested (new-project, run, defect) | 5 new E2E spec (Playwright) | 3 gün |

---

# SPRINT 1 — HAFTA 1 (Mon 6/16 - Fri 6/20)

## Tema: Kritik Mega-Component Split + Type Foundation

### Sprint Hedef
- ✅ new-project split (Wizard, Form, Submit) — **test possible** hale getir
- ✅ Type foundation (@neurex/contracts) — **AI Provider, TaskType, Config** safe
- ✅ AppShell extract **SidebarNav** (30% progress) — foundation
- ✅ TanStack Query key factory audit başlat
- ✅ TypeScript strict mode baseline (10 critical error)
- **Success:** new-project unit test pass, 0 type regression, bundle +50KB tolerance

---

## Task Breakdown (Sprint 1)

### DAY 1-2 (Mon-Tue): new-project/page.tsx Split — **Dev A**

#### Task 1.1: Wizard Component Extract (2835 → 800 satır)
```
Goal: apps/web/app/new-project/_components/ProjectWizard.tsx
- Props: onComplete(project) → navigation
- State: step, formData (local)
- Effect: none (parent-driven)
- Test: <ProjectWizard onComplete={mockFn} /> → button click → onComplete called
```

**Subtasks:**
1. Create `_components/` directory
2. Move Wizard UI (steps, progress bar) → component
3. Extract step state (useState) → component local
4. Move step change logic → local handler
5. Props type: `interface ProjectWizardProps { onComplete: (p: Project) => void }`

**Acceptance Criteria:**
- [ ] Component <300 lines
- [ ] No prop drilling (1 level max)
- [ ] Testable: step change via buttons
- [ ] Snapshot: `__tests__/ProjectWizard.spec.tsx`

**Risk:** Parent rerender if step state shared — **use local state only**

---

#### Task 1.2: FormFields Component Extract (800 → 400 satır)
```
Goal: apps/web/app/new-project/_components/ProjectFormFields.tsx
- Props: initialData?, onChange(field, value)
- Presentational (no API, no useState)
```

**Subtasks:**
1. Move all form input (Name, Desc, AI Provider, Env) → component
2. All state → parent (page.tsx)
3. onChange callbacks → parent-driven
4. Field-level validation → Zod schema (task 1.3)

**Acceptance Criteria:**
- [ ] Pure presentational (0 useState)
- [ ] onChange fires on every keystroke
- [ ] Zod validation applied (error display)

---

#### Task 1.3: Form Validation Standard (Zod Schema)
```
Goal: apps/web/app/new-project/schema.ts
```

**Subtasks:**
1. Define ProjectFormSchema (Zod)
   - name: string().min(1).max(100)
   - description: string().optional()
   - aiProvider: enum(PROVIDERS)
   - environments: array(object({name, url}))

2. Create useProjectForm hook
   ```typescript
   export function useProjectForm(onSubmit: (p: Project) => Promise<void>) {
     const { register, handleSubmit, formState: { errors } } = useForm({
       resolver: zodResolver(ProjectFormSchema),
       defaultValues: {}
     });
     return { register, handleSubmit, errors };
   }
   ```

3. Wire into ProjectFormFields
   - onChange → register('field').onChange
   - error display → errors['field']?.message

**Acceptance Criteria:**
- [ ] Zod schema 100% coverage (all fields)
- [ ] useProjectForm hook exported
- [ ] FormFields integrate with react-hook-form
- [ ] Test: invalid input → error message displayed

---

#### Task 1.4: Summary Component Extract
```
Goal: apps/web/app/new-project/_components/ProjectSummary.tsx
- Props: project (readonly display)
- Edit/Submit buttons → onClick handlers
```

**Subtasks:**
1. Move review/confirmation step → component
2. Display: name, description, AI provider, environments
3. Buttons: Edit, Confirm Create
4. onClick → parent handlers

**Acceptance Criteria:**
- [ ] Read-only (no input fields)
- [ ] Display all project fields
- [ ] Button handlers via props

---

#### Task 1.5: Parent page.tsx Refactor (2835 → 400 satır)
```
Goal: apps/web/app/new-project/page.tsx
```

**Logic Flow:**
```typescript
export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState('wizard'); // 'wizard' | 'form' | 'summary'
  const [formData, setFormData] = useState<ProjectFormData>({});
  const [project, setProject] = useState<Project | null>(null);
  const mutation = useMutation({
    mutationFn: (data) => apiClient.post('/projects', data),
    onSuccess: (p) => { setProject(p); setStep('summary'); }
  });

  const handleWizardComplete = () => setStep('form');
  const handleFormSubmit = (data) => mutation.mutate(data);
  const handleConfirm = () => router.push(`/projects/${project.id}`);

  return (
    <>
      {step === 'wizard' && <ProjectWizard onComplete={handleWizardComplete} />}
      {step === 'form' && <ProjectFormFields onChange={setFormData} onSubmit={handleFormSubmit} />}
      {step === 'summary' && <ProjectSummary project={project!} onConfirm={handleConfirm} />}
    </>
  );
}
```

**Acceptance Criteria:**
- [ ] page.tsx <200 lines
- [ ] 3 sub-components mount/unmount per step
- [ ] No prop drilling (props pass 1 level)
- [ ] Full E2E: wizard → form → summary → navigate

---

### DAY 2-3 (Tue-Wed): Type Foundation (@neurex/contracts) — **Dev B**

#### Task 2.1: Create @neurex/contracts Package
```
Goal: packages/contracts/ (new)
Structure:
  - src/
    - ai-provider.ts (AI Provider, TaskType, Model enums)
    - config.ts (Environment, Config schema)
    - project.ts (Project, ProjectForm schema)
    - index.ts (export *)
  - tsconfig.json
  - package.json
```

**Subtasks:**
1. Create directory + npm workspaces entry
2. Define AI Provider types:
   ```typescript
   export const AI_PROVIDERS = ['ollama', 'vllm', 'groq', 'gemini'] as const;
   export type AIProvider = typeof AI_PROVIDERS[number];
   
   export const TASK_TYPES = ['fast', 'analyst', 'coder'] as const;
   export type TaskType = typeof TASK_TYPES[number];
   
   export type AIProviderConfig = {
     type: AIProvider;
     apiKey?: string;
     baseUrl?: string;
     model: string;
   };
   ```

3. Zod schema:
   ```typescript
   export const AIProviderSchema = z.object({
     type: z.enum(AI_PROVIDERS),
     model: z.string().min(1),
     apiKey: z.string().optional(),
     baseUrl: z.string().url().optional()
   });
   ```

4. Project schema:
   ```typescript
   export const ProjectFormSchema = z.object({
     name: z.string().min(1).max(100),
     description: z.string().optional(),
     aiProvider: AIProviderSchema,
     environments: z.array(z.object({
       name: z.string(),
       url: z.string().url()
     }))
   });
   ```

**Acceptance Criteria:**
- [ ] TypeScript compiles (0 error)
- [ ] Exported types imported in apps/web
- [ ] Zod schema integrates with react-hook-form
- [ ] Test: schema validation (valid/invalid input)

---

#### Task 2.2: Wire @neurex/contracts into apps/web
```
Goal: Replace inline types in apps/web
```

**Subtasks:**
1. Remove `apps/web/lib/types/ai-provider.ts`
2. Import from @neurex/contracts:
   ```typescript
   import { AIProvider, TaskType, ProjectFormSchema } from '@neurex/contracts';
   ```
3. Update 12 files using old types (grep AI_PROVIDER, TaskType)
4. Update form schema:
   ```typescript
   import { ProjectFormSchema } from '@neurex/contracts';
   // useForm({ resolver: zodResolver(ProjectFormSchema) })
   ```

**Acceptance Criteria:**
- [ ] 0 TypeScript error after import
- [ ] All 12 dependent files compile
- [ ] No runtime type mismatch

---

### DAY 3-4 (Wed-Thu): AppShell Extract (Partial) — **Dev C**

#### Task 3.1: SidebarNav Component Extract
```
Goal: apps/web/components/AppShell/_components/SidebarNav.tsx
```

**Subtasks:**
1. Extract navigation items (Home, Projects, Settings, Help)
   - Props: items[], activeRoute, onNavigate(route)
   - Presentational: no navigation logic
2. Logo + collapsed state handling
3. User quick-access menu (separate task)

**Acceptance Criteria:**
- [ ] Component <150 lines
- [ ] onNavigate prop fires on item click
- [ ] Collapsed state toggleable

---

#### Task 3.2: ProductPicker Component Extract
```
Goal: apps/web/components/AppShell/_components/ProductPicker.tsx
```

**Subtasks:**
1. Extract: project selector dropdown
   - Props: projects[], activeProjectId, onSelect(id)
   - Presentational: fetch logic stays in parent

**Acceptance Criteria:**
- [ ] Dropdown toggles on click
- [ ] onSelect fires with project ID

---

### DAY 4-5 (Thu-Fri): Query Key Audit Kickoff + TypeScript Baseline — **Dev A + B**

#### Task 4.1: Query Key Factory Audit (50 files)
```
Goal: apps/web/lib/query-keys.ts (centralize all keys)
```

**Subtasks:**
1. Scan 50 files: grep -r "queryKey.*=" → list all key patterns
2. Classify:
   - ✅ Using factory function (keep)
   - ❌ String literals (convert)
   - ❌ Inconsistent naming (fix)
3. Create factory for missing domains:
   ```typescript
   export const queryKeys = {
     projects: {
       all: ['projects'] as const,
       lists: () => [...queryKeys.projects.all, 'list'] as const,
       list: (org?: string) => [...queryKeys.projects.lists(), org] as const,
       details: () => [...queryKeys.projects.all, 'detail'] as const,
       detail: (id: string) => [...queryKeys.projects.details(), id] as const,
     },
     runs: {
       all: ['runs'] as const,
       // similar structure
     }
   };
   ```
4. Update 20 high-priority hooks

**Acceptance Criteria:**
- [ ] Factory covers 80% of domains
- [ ] 20 hooks migrated (new-project, case, run, defect)
- [ ] tsc --noEmit (0 error)

---

#### Task 4.2: TypeScript Strict Mode Baseline
```
Goal: Fix 10 critical type errors
```

**Subtasks:**
1. tsc --strict > type-errors.txt
2. Filter critical (implicit any, missing types):
   - AppShell.tsx: useState inferred types
   - use-management.ts: return type missing
   - Schemas: params type mismatch
3. Fix top 10 errors:
   - Add explicit types (useState<T>)
   - API response types
   - Component prop types

**Acceptance Criteria:**
- [ ] 10 errors → 0
- [ ] No regression (existing tests pass)

---

## Resource Allocation (Sprint 1)

| Role | Name | Task | Days |
|------|------|------|------|
| Dev A | — | 1.1-1.5 (new-project), 4.2 | 4 days |
| Dev B | — | 2.1-2.2 (@neurex/contracts), 4.1 | 4 days |
| Dev C | — | 3.1-3.2 (AppShell partial) | 2 days |
| Designer | — | Review Task 2.1 (type UX), Task 1.3 (form UX) | 1 day |
| QA | — | Test 1.1-1.5 (new-project happy path), Test 2.2 (contract import) | 2 days |

**Total:** 3 devs full-time + designer + QA

---

## Dependencies (Sprint 1)

```
Task 1.1-1.5 (new-project split)
  └─ Task 1.3 (Zod schema) — BLOCKS 1.2, 1.4
  └─ NO EXTERNAL DEPENDENCY

Task 2.1 (@neurex/contracts)
  └─ NO DEPENDENCY (parallel with Task 1)
  └─ BLOCKS Task 2.2

Task 2.2 (wire contracts)
  └─ DEPENDS ON Task 2.1
  └─ BLOCKS Task 1.5 type update (optional, can be done in Task 1.5)

Task 3.1-3.2 (AppShell extract)
  └─ NO DEPENDENCY (parallel)
  └─ 50% progress only

Task 4.1 (query key audit)
  └─ BLOCKS none (low-risk, can extend to Sprint 2)
  └─ DEPENDS ON Task 4.2 for baseline

Task 4.2 (TypeScript baseline)
  └─ DEPENDS ON tsc run (can start day 1)
```

---

## Success Criteria (Sprint 1)

### Code Quality
- [ ] new-project.tsx 2835 → <400 lines
- [ ] new-project split into 4 files (<300 lines each)
- [ ] @neurex/contracts compiles (0 error)
- [ ] 20 query keys migrated (factory-driven)
- [ ] 10 TypeScript critical errors fixed

### Testing
- [ ] new-project unit test: 4 scenarios (wizard, form, summary, submit)
  - Wizard: step change on button click
  - Form: validation error display
  - Summary: display project review
  - Submit: API call + navigate
- [ ] @neurex/contracts test: schema validation (valid/invalid input)
- [ ] AppShell partial: SidebarNav snapshot test

### Performance
- [ ] Bundle size: <500KB (baseline check)
- [ ] new-project LCP: <1.5s (measure before/after)
- [ ] No prop drilling >1 level (lint rule check)

### Metrics
- [ ] TypeScript errors: 40 → 30 (25% reduction)
- [ ] Test coverage (new-project): 80%
- [ ] Code review: 0 comments on critical path

---

## Risk & Mitigation (Sprint 1)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| new-project split breaks E2E | Medium | High | Keep old page until all tests pass, then flip |
| @neurex/contracts circular import | Low | High | Use relative imports in contracts, avoid circular |
| Query key factory inconsistency | Low | Medium | Audit all usages before merge, lint rule |
| TypeScript cascade fix | Medium | Medium | Fix base types first, then dependents (bottom-up) |
| AppShell extract incomplete | Low | Low | Mark as 50% progress, finish Sprint 2 |

---

---

# SPRINT 2 — HAFTA 2 (Mon 6/23 - Fri 6/27)

## Tema: Hook Monolith Split + Query Consistency + Responsive Foundation

### Sprint Hedef
- ✅ use-management.ts split (2604 → 6 files, ~400 lines each)
- ✅ Query key consistency (50 files, 100% coverage)
- ✅ TypeScript strict mode (40 → 5 errors)
- ✅ Form validation standardization (20 forms → Zod)
- ✅ AppShell extract complete (882 → 200 lines)
- **Success:** 0 bundle regression, Lighthouse ≥75, 10+ new unit tests

---

## Task Breakdown (Sprint 2)

### DAY 1-2 (Mon-Tue): use-management Hook Split Phase 1 — **Dev A**

#### Task 5.1: Domain Analysis & Split Plan
```
Goal: Map use-management domains + create 6 new hooks
```

**Current use-management.ts domains (2604 lines):**
1. Test case CRUD (300 lines)
2. Test case execution (350 lines)
3. Run management (300 lines)
4. Defect management (400 lines)
5. Coverage analytics (350 lines)
6. Report generation (304 lines)

**Subtasks:**
1. Create split map:
   ```
   hooks/
     use-test-cases.ts (300) ← test case CRUD
     use-case-execution.ts (350) ← step run, result
     use-runs.ts (300) ← run lifecycle
     use-defects.ts (400) ← defect CRUD
     use-coverage.ts (350) ← analytics
     use-reports.ts (304) ← PDF export
     index.ts (exports all)
   ```

2. Extract imports per domain (apiClient, schema, type)
3. Extract useState/useCallback per domain
4. Map internal function calls → cross-hook dependencies

**Acceptance Criteria:**
- [ ] Split plan documented (6 files mapped)
- [ ] Dependencies identified (circular check)
- [ ] No file >400 lines (target: ~300)

---

#### Task 5.2: use-test-cases.ts Extract
```
Goal: Test case CRUD operations
```

**Subtasks:**
1. Extract:
   - createTestCase(data)
   - updateTestCase(id, data)
   - deleteTestCase(id)
   - listTestCases(projectId)
   - getTestCase(id)
   
2. Move useMutation/useQuery calls
3. Error handling (same as original)
4. Type: `export interface UseTestCases { ... }`

**Acceptance Criteria:**
- [ ] <300 lines
- [ ] All CRUD operations exported
- [ ] Error handling preserved
- [ ] Test: createTestCase → apiClient.post called

---

#### Task 5.3: use-case-execution.ts Extract
```
Goal: Test case execution + step management
```

**Subtasks:**
1. Extract:
   - executeTestCase(id)
   - executeStep(caseId, stepId)
   - getStepResult(stepId)
   - updateStepStatus(stepId, status)

2. Move execution state (loading, result, error)
3. Retry logic + timeout handling

**Acceptance Criteria:**
- [ ] <350 lines
- [ ] Execution flow testable
- [ ] Step status update works

---

#### Task 5.4: use-runs.ts Extract
```
Goal: Test run lifecycle
```

**Subtasks:**
1. Extract:
   - createRun(config)
   - getRun(id)
   - listRuns(projectId, filter)
   - updateRunStatus(id, status)
   - cancelRun(id)

2. Move run state + polling (if any)

**Acceptance Criteria:**
- [ ] <300 lines
- [ ] Run polling logic preserved
- [ ] Filter parameters typed

---

#### Task 5.5: use-defects.ts Extract
```
Goal: Defect management (CRUD + assignment)
```

**Subtasks:**
1. Extract:
   - createDefect(caseId, data)
   - updateDefect(id, data)
   - assignDefect(id, userId)
   - listDefects(projectId, filter)
   - getDefect(id)

2. Move defect state

**Acceptance Criteria:**
- [ ] <400 lines
- [ ] Defect assignment workflow works
- [ ] Filter + pagination typed

---

### DAY 2-3 (Tue-Wed): use-management Hook Split Phase 2 — **Dev B**

#### Task 5.6: use-coverage.ts Extract
```
Goal: Coverage analytics
```

**Subtasks:**
1. Extract:
   - getCoverageStats(projectId)
   - getCoverageByModule(projectId)
   - getCoverageTrend(projectId, days)
   
2. Move analytics data + chart state

**Acceptance Criteria:**
- [ ] <350 lines
- [ ] Coverage calculations correct
- [ ] Time-series data typed

---

#### Task 5.7: use-reports.ts Extract
```
Goal: Report generation
```

**Subtasks:**
1. Extract:
   - generateReport(config)
   - exportPDF(data)
   - exportCSV(data)
   - listReports(projectId)

2. Move export logic

**Acceptance Criteria:**
- [ ] <304 lines
- [ ] Export formats work (PDF, CSV)

---

#### Task 5.8: Hook Index + Integration Test
```
Goal: apps/web/lib/hooks/index.ts (export all)
```

**Subtasks:**
1. Create barrel export:
   ```typescript
   export { useTestCases } from './use-test-cases';
   export { useCaseExecution } from './use-case-execution';
   export { useRuns } from './use-runs';
   export { useDefects } from './use-defects';
   export { useCoverage } from './use-coverage';
   export { useReports } from './use-reports';
   ```

2. Integration test: import all hooks, verify no circular deps
3. Update imports in 20 components

**Acceptance Criteria:**
- [ ] All hooks importable
- [ ] 0 circular dependency
- [ ] 20 components compile
- [ ] Bundle size check (should decrease ~30KB)

---

### DAY 3-4 (Wed-Thu): Query Key 100% Coverage — **Dev A + B**

#### Task 6.1: Complete Query Key Factory
```
Goal: 100% query key coverage (50 domains)
```

**Subtasks:**
1. Extend queryKeys factory:
   ```typescript
   export const queryKeys = {
     projects: { ... },
     runs: { ... },
     cases: { ... },
     defects: { ... },
     coverage: { ... },
     reports: { ... },
     users: { ... },
     organizations: { ... },
     // 42 more domains...
   };
   ```

2. Migrate 50 files:
   - High priority (10): new-project, case, run, defect, coverage, report, auth, team, onboarding, settings
   - Medium priority (20): dashboard, admin, notifications, integrations, etc.
   - Low priority (20): lesser-used pages

3. Lint rule: disallow direct string queryKey (eslint custom)

**Acceptance Criteria:**
- [ ] All 50 domains covered
- [ ] 30 files migrated (high+medium priority)
- [ ] tsc --noEmit (0 error)
- [ ] eslint --fix (0 violations)

---

#### Task 6.2: Query Key Testing
```
Goal: Verify key consistency (unit test)
```

**Subtasks:**
1. Test: key uniqueness (no duplicates)
   ```typescript
   test('query keys are unique', () => {
     const keys = flattenQueryKeys(queryKeys);
     expect(new Set(keys).size).toBe(keys.length);
   });
   ```

2. Test: invalidation patterns
   ```typescript
   test('invalidation cascades', () => {
     queryClient.setQueryData(queryKeys.cases.list(), []);
     queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
     expect(queryClient.getQueryData(queryKeys.cases.list())).toBeUndefined();
   });
   ```

**Acceptance Criteria:**
- [ ] All key tests pass
- [ ] Invalidation patterns verified

---

### DAY 4-5 (Thu-Fri): Form Validation Standard + TypeScript Final Push — **Dev C**

#### Task 7.1: Standardize Form Validation (20 forms → Zod)
```
Goal: All forms use Zod + react-hook-form
```

**Forms to migrate:**
1. ProjectForm (done Sprint 1)
2. TestCaseForm (300 lines) — use case creation
3. DefectForm (250 lines) — defect submission
4. ReportFilterForm (200 lines) — analytics filter
5-20. Other forms (admin, settings, integrations, etc.)

**Per form:**
1. Create schema file: `forms/test-case-schema.ts`
2. Define Zod schema (all fields, validations)
3. Create useForm hook:
   ```typescript
   export function useTestCaseForm(onSubmit: (data) => Promise<void>) {
     const { register, handleSubmit, formState: { errors } } = useForm({
       resolver: zodResolver(TestCaseFormSchema),
     });
     return { register, handleSubmit, errors };
   }
   ```
4. Update form component: wire register/errors

**Acceptance Criteria:**
- [ ] 20 forms use Zod
- [ ] 0 inline validation
- [ ] Form error tests (5 scenarios each)
- [ ] Shared schema across backend/frontend (via @neurex/contracts)

---

#### Task 7.2: TypeScript Strict Mode Final Push
```
Goal: 40 errors → 5 (error budget for Phase 2)
```

**Subtasks:**
1. Fix remaining errors:
   - useCallback typing (missing dependency arrays)
   - Component prop forwarding (React.FC vs React.ReactNode)
   - API response shape mismatches

2. Update tsconfig.json:
   ```json
   {
     "compilerOptions": {
       "strict": true,
       "noImplicitAny": true,
       "noImplicitThis": true,
       "strictNullChecks": true,
       "strictFunctionTypes": true
     }
   }
   ```

**Acceptance Criteria:**
- [ ] 40 → 5 errors (88% reduction)
- [ ] No regression tests
- [ ] CI passes (tsc --noEmit)

---

### DAY 5 (Fri): AppShell Complete + Component Tier Definition — **Dev C**

#### Task 8.1: AppShell Complete Extract
```
Goal: 882 → <200 lines (finish Sprint 1 work)
```

**Remaining:**
1. UserMenu component (was setState)
2. Breadcrumb component
3. Notification bell component
4. Layout container refactor

**Acceptance Criteria:**
- [ ] AppShell <200 lines
- [ ] 4 sub-components extracted
- [ ] 0 useState in AppShell
- [ ] Test: sidebar toggle, menu open/close

---

#### Task 8.2: Component Tier Definition (ADR-0015)
```
Goal: Document + enforce container/presentational/smart tier
```

**ADR-0015 Outline:**
```markdown
# ADR-0015: Component Tier Classification

## Decision
Components classified into 3 tiers:

1. **Presentational (View)** — no useState, no useEffect, no API
   - Pure props-in, JSX-out
   - Example: ProjectCard, Button, Badge
   - Location: components/ or _components/
   
2. **Smart (Container)** — useState, useEffect, API call
   - Business logic + UI composition
   - Example: ProjectList (fetch + filter + render)
   - Location: (page.tsx or _components/ProjectListContainer.tsx)
   
3. **Domain Hook** — data fetching, state management
   - Example: useProjects, useTestCases
   - Location: lib/hooks/

## Enforcement
- ESLint rule: no useState in components/ (only _components/)
- Naming: useXXX → hook, XXXContainer.tsx → smart, XXX.tsx → presentational
- Code review checklist: tier mismatch catch
```

**Subtasks:**
1. Write ADR (1h)
2. Create ESLint rule (custom rule: no useState in components/)
3. Update 50 components (tag tier in comment)
4. Document in CLAUDE.md

**Acceptance Criteria:**
- [ ] ADR-0015 merged
- [ ] ESLint rule written + passing
- [ ] 50 components tagged
- [ ] 0 tier violations

---

## Resource Allocation (Sprint 2)

| Role | Name | Task | Days |
|------|------|------|------|
| Dev A | — | 5.1-5.4 (hook split phase 1), 6.1 | 4 days |
| Dev B | — | 5.6-5.8 (hook split phase 2), 6.2 | 4 days |
| Dev C | — | 7.1-7.2 (form validation, TS), 8.1-8.2 | 5 days |
| Designer | — | Review form validation UX (Task 7.1) | 1 day |
| QA | — | Test hooks (5.1-5.8), forms (7.1), AppShell (8.1) | 3 days |

---

## Dependencies (Sprint 2)

```
Task 5.1-5.8 (use-management split)
  └─ NO EXTERNAL DEPENDENCY (parallel)
  └─ DEPENDS ON Sprint 1 completion (type foundation)

Task 6.1-6.2 (query key factory)
  └─ DEPENDS ON Task 4.1 (Sprint 1 kickoff)
  └─ BLOCKS Task 7.1 (form validation depends on query keys)

Task 7.1 (form validation)
  └─ DEPENDS ON Task 2.1 (@neurex/contracts)
  └─ DEPENDS ON Task 6.1 (query keys for fetching)

Task 8.1-8.2 (AppShell + ADR)
  └─ NO DEPENDENCY (parallel)
```

---

## Success Criteria (Sprint 2)

### Code Quality
- [ ] use-management.ts 2604 → 6 files (~400 lines each)
- [ ] Total hook size reduction: 2604 → ~2000 lines (23% reduction via better organization)
- [ ] Query keys: 50 files → 100% factory-driven
- [ ] Form validation: 20 forms → 100% Zod
- [ ] TypeScript errors: 40 → 5 (88% reduction)
- [ ] AppShell: 882 → <200 lines

### Testing
- [ ] Hook unit tests: 6 hooks × 3 scenarios = 18 tests
- [ ] Query key tests: uniqueness + invalidation
- [ ] Form validation tests: 20 forms × 3 scenarios = 60 tests
- [ ] AppShell tests: sidebar, menu, breadcrumb, notification

### Performance
- [ ] Bundle size: -50KB (hook split)
- [ ] No regression (compare Sprint 1 baseline)
- [ ] LCP: <1.5s (case, run, defect pages)
- [ ] Query key efficiency (no over-fetching)

### Metrics
- [ ] Code coverage: +15% (new hook tests)
- [ ] TypeScript strict: 88% compliance
- [ ] Linter: 0 violations (query key + component tier)
- [ ] Review comments: <5 per 200 lines

---

## Risk & Mitigation (Sprint 2)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Hook split circular dependency | Medium | High | Use explicit imports, no barrel exports between hooks |
| Query key migration cascades | Medium | High | Migrate high-priority (10) first, monitor bundle |
| Form validation breaks UI | Low | Medium | Keep old forms as fallback, feature flag new ones |
| TypeScript cascade fixes | Medium | Medium | Fix base types, then dependents (layers approach) |

---

---

# SPRINT 3 — HAFTA 3 (Mon 6/30 - Fri 7/4)

## Tema: Responsive Design + E2E Test Coverage + Quality Gate

### Sprint Hedef
- ✅ Responsive refactor (5 critical pages: new-project, case, run, defect, dashboard)
- ✅ E2E test coverage (5 critical paths)
- ✅ Lighthouse ≥85 (all pages)
- ✅ 0 TypeScript error
- ✅ Bundle <500KB
- **Success:** FAZA 0 complete, production-ready code

---

## Task Breakdown (Sprint 3)

### DAY 1-2 (Mon-Tue): Critical Page Responsive Refactor — **Dev A**

#### Task 9.1: new-project Page Responsive
```
Goal: Mobile-first responsive (breakpoints: 375, 768, 1024)
```

**Current state (Sprint 1):**
- Desktop: 4-step wizard → works
- Mobile: 2835 satır → 400 satır (split done)

**Subtasks:**
1. Add Tailwind breakpoint utilities:
   - sm: 640px (phone landscape)
   - md: 768px (tablet)
   - lg: 1024px (desktop)

2. ProjectWizard responsive:
   - Desktop: horizontal steps, left-aligned
   - Tablet: vertical steps, compact
   - Mobile: collapsed steps (1/4 indicator)

3. ProjectFormFields responsive:
   - Desktop: 2-column layout
   - Mobile: 1-column stack

4. Test: responsive behavior at 375, 768, 1024

**Acceptance Criteria:**
- [ ] 375px: 1 column, no horizontal scroll
- [ ] 768px: 2 column, readable
- [ ] 1024px: full layout, optimal spacing
- [ ] Touch targets: ≥48px (a11y)
- [ ] Responsive test: 3 breakpoints pass

---

#### Task 9.2: Case Detail Page Responsive
```
Goal: Mobile case view + tab collapse
```

**Subtasks:**
1. Desktop: 3-column (sidebar, detail, actions)
2. Tablet: 2-column (collapse sidebar to hamburger)
3. Mobile: 1-column (full-width detail, action drawer)

4. Tab navigation:
   - Desktop: horizontal tabs
   - Mobile: collapsed menu (icon + badge)

5. Steps sidebar:
   - Desktop: vertical list
   - Mobile: horizontal scroll or accordion

**Acceptance Criteria:**
- [ ] Mobile: hamburger sidebar
- [ ] Mobile: action drawer vs. sidebar
- [ ] All tabs accessible (no horizontal scroll)

---

#### Task 9.3: Run Page Responsive
```
Goal: Mobile test run view
```

**Subtasks:**
1. Desktop: run steps + results side-by-side
2. Mobile: stacked (step → result)

3. Step result cards:
   - Desktop: 800px wide
   - Mobile: full-width, smaller fonts

4. Charts (if any):
   - Desktop: full chart
   - Mobile: simplified view (summary stats)

**Acceptance Criteria:**
- [ ] Mobile stacked layout works
- [ ] Charts readable on mobile
- [ ] Touch interactions work

---

#### Task 9.4: Defect Page Responsive
```
Goal: Mobile defect list + detail
```

**Subtasks:**
1. Desktop: table (20 columns sortable/filterable)
2. Mobile: card list (5 key columns)

3. Defect detail:
   - Desktop: 3-column (info, comments, attachments)
   - Mobile: tabbed view

4. Filters:
   - Desktop: sidebar
   - Mobile: modal/sheet

**Acceptance Criteria:**
- [ ] Card list on mobile (no table)
- [ ] Filter modal works
- [ ] Detail tabs accessible

---

### DAY 2-3 (Tue-Wed): Dashboard Page Responsive + Virtualization — **Dev B**

#### Task 10.1: Dashboard Responsive
```
Goal: Mobile dashboard (widgets collapse/reorder)
```

**Current state:**
- Dashboard: 50+ widgets, inline render block (Sprint 1 finding)

**Subtasks:**
1. Desktop: 4-column grid
2. Tablet: 2-column grid
3. Mobile: 1-column (vertical stack)

4. Widget collapsing:
   - Desktop: all expanded
   - Tablet: collapsible sections
   - Mobile: accordion (1 open at a time)

5. Performance fix:
   - Virtual scrolling (react-window):
     ```typescript
     <FixedSizeList
       height={window.innerHeight}
       itemCount={widgets.length}
       itemSize={400}
       width="100%"
     >
       {({ index, style }) => <WidgetCard widget={widgets[index]} style={style} />}
     </FixedSizeList>
     ```

**Acceptance Criteria:**
- [ ] Dashboard renders mobile (1-column)
- [ ] Virtual scrolling: 50 widgets in <500ms
- [ ] No layout shift on widget collapse
- [ ] Touch-friendly collapse buttons

---

#### Task 10.2: Lighthouse Optimization
```
Goal: Lighthouse ≥85 (all pages)
```

**Current state (Sprint 1 baseline):**
- Lighthouse: 65 (hedef: ≥85)
- TTI: 3.2s (hedef: <1.5s)
- Bundle: 650KB (hedef: <500KB)

**Subtasks:**
1. Image optimization:
   - next/image + blur placeholder
   - WebP + fallback
   - Lazy loading (loading="lazy")

2. Code splitting:
   - dynamic import for heavy components (PDFExport, Charts)
   - Route-based code splitting

3. CSS optimization:
   - Unused CSS purge (PurgeCSS)
   - CSS-in-JS → Tailwind (fewer payloads)
   - Critical CSS inline

4. Script optimization:
   - Defer non-critical JS
   - Web Worker for analytics

5. Network optimization:
   - Compression (gzip)
   - Font subsetting (WOFF2 only)

**Metrics to track:**
- FCP: First Contentful Paint <1.5s
- LCP: Largest Contentful Paint <1.5s
- CLS: Cumulative Layout Shift <0.1
- TTI: Time to Interactive <1.5s

**Acceptance Criteria:**
- [ ] Lighthouse ≥85 (all pages)
- [ ] LCP <1.5s (case, run, defect, dashboard)
- [ ] TTI <1.5s
- [ ] No regression from Sprint 1-2

---

### DAY 3-4 (Wed-Thu): E2E Test Coverage — **QA Lead**

#### Task 11.1: Critical Path E2E Tests (5 scenarios)
```
Goal: Playwright E2E: new-project, run, defect, case, dashboard
```

**Test 1: New Project Creation (Happy Path)**
```typescript
test('create project: name → AI provider → environments → confirm', async ({ page }) => {
  await page.goto('/new-project');
  
  // Wizard step
  await page.click('[data-testid="wizard-next"]');
  
  // Form step
  await page.fill('[data-testid="project-name"]', 'Test Project');
  await page.fill('[data-testid="project-desc"]', 'Test description');
  await page.selectOption('[data-testid="ai-provider"]', 'ollama');
  
  // Summary step
  await page.click('[data-testid="confirm-create"]');
  
  // Navigate
  await expect(page).toHaveURL('/projects/123');
});
```

**Test 2: Test Case Execution (Happy Path)**
```typescript
test('execute test case: start → monitor → results', async ({ page }) => {
  await page.goto('/projects/123/cases/456');
  
  // Start execution
  await page.click('[data-testid="execute-btn"]');
  
  // Monitor steps
  const stepResults = await page.locator('[data-testid="step-result"]').all();
  expect(stepResults.length).toBeGreaterThan(0);
  
  // View results
  await expect(page.locator('[data-testid="run-status"]')).toContainText('passed');
});
```

**Test 3: Defect Creation (Happy Path)**
```typescript
test('create defect from case result', async ({ page }) => {
  // Prerequisite: failed test case
  await page.goto('/projects/123/cases/456/runs/789');
  
  // Create defect
  await page.click('[data-testid="create-defect-btn"]');
  await page.fill('[data-testid="defect-title"]', 'UI button not clickable');
  await page.fill('[data-testid="defect-description"]', 'Button disabled unexpectedly');
  
  // Submit
  await page.click('[data-testid="submit-defect"]');
  
  // Verify redirect
  await expect(page).toHaveURL(/\/defects\/\d+/);
});
```

**Test 4: Dashboard Load + Widgets (Happy Path)**
```typescript
test('dashboard: load widgets, filter, refresh', async ({ page }) => {
  await page.goto('/dashboard');
  
  // Wait for widgets
  await page.waitForLoadState('networkidle');
  
  // Verify widgets
  const widgets = await page.locator('[data-testid="dashboard-widget"]').count();
  expect(widgets).toBeGreaterThan(5);
  
  // Filter
  await page.selectOption('[data-testid="filter-project"]', '123');
  await page.click('[data-testid="apply-filter"]');
  
  // Refresh
  await page.click('[data-testid="refresh-btn"]');
  await expect(page.locator('[data-testid="loading"]')).toBeHidden();
});
```

**Test 5: Responsive Mobile (new-project on mobile)**
```typescript
test('new-project responsive on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/new-project');
  
  // Wizard visible
  await expect(page.locator('[data-testid="wizard-steps"]')).toBeVisible();
  
  // No horizontal scroll
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth
  );
  expect(overflow).toBe(true);
  
  // Touch target size
  const button = page.locator('[data-testid="wizard-next"]');
  const box = await button.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(48);
});
```

**Subtasks:**
1. Create tests/e2e/ directory
2. Write 5 test files (Playwright)
3. Setup test data (seed DB with projects, cases, etc.)
4. Configure CI/CD (GitHub Actions) — run on PR
5. Baseline: all tests pass

**Acceptance Criteria:**
- [ ] 5 tests pass locally + CI
- [ ] Coverage: 5 critical paths (100%)
- [ ] Test data consistent
- [ ] Screenshots captured (failure debugging)

---

#### Task 11.2: Error Path E2E Tests (3 scenarios)
```
Goal: Negative test coverage (error handling)
```

**Test 1: New Project Validation Error**
```typescript
test('new-project form validation error', async ({ page }) => {
  await page.goto('/new-project');
  // Skip to form step
  await page.click('[data-testid="wizard-next"]');
  
  // Submit without name
  await page.click('[data-testid="submit-form"]');
  
  // Verify error
  await expect(page.locator('[data-testid="error-name"]')).toContainText('required');
});
```

**Test 2: API Error Handling (500)**
```typescript
test('handle API 500 error gracefully', async ({ page }) => {
  // Mock API error
  await page.route('**/api/projects', route =>
    route.abort('serverfault')
  );
  
  await page.goto('/new-project');
  await page.click('[data-testid="submit-form"]');
  
  // Verify error toast
  await expect(page.locator('[data-testid="toast-error"]')).toContainText('error');
  await expect(page.locator('[data-testid="retry-btn"]')).toBeVisible();
});
```

**Test 3: Network Timeout**
```typescript
test('handle network timeout', async ({ page }) => {
  // Mock slow network
  await page.route('**/api/**', route =>
    new Promise(() => {}) // Never resolve
  );
  
  await page.goto('/dashboard');
  
  // After 5s, show error
  await page.waitForTimeout(6000);
  await expect(page.locator('[data-testid="toast-timeout"]')).toBeVisible();
});
```

**Acceptance Criteria:**
- [ ] 3 error path tests pass
- [ ] Error messages user-friendly
- [ ] Retry mechanism works

---

### DAY 4-5 (Thu-Fri): Final Quality Gate + Documentation — **Dev + QA**

#### Task 12.1: Quality Gate Audit
```
Goal: FAZA 0 readiness check
```

**Checklist:**
```
Code Quality:
  [ ] TypeScript: 0 error (tsc --noEmit)
  [ ] Linter: 0 violation (eslint + ruff)
  [ ] Code coverage: 80% (critical paths)
  [ ] No console.warn/error in production build

Performance:
  [ ] Bundle: <500KB (gzip)
  [ ] LCP: <1.5s (all pages)
  [ ] TTI: <1.5s
  [ ] Lighthouse: ≥85
  [ ] Memory: <100MB on load

Tests:
  [ ] Unit tests: 200+ pass
  [ ] Integration tests: 50+ pass
  [ ] E2E tests: 8 pass (5 happy + 3 error)
  [ ] Regression: 0 new failures

Accessibility (a11y):
  [ ] WCAG AA: 0 violations
  [ ] Touch targets: ≥48px
  [ ] Color contrast: ≥4.5:1
  [ ] Keyboard navigation: all pages

Security:
  [ ] XSS: 0 issues (sanitize HTML)
  [ ] CSRF: token check on all mutations
  [ ] CORS: same-origin + API whitelist
  [ ] Secrets: no hardcoded values (.env)

Documentation:
  [ ] ADR-0015 merged (component tier)
  [ ] CLAUDE.md updated (new guidelines)
  [ ] Component storybook: 20+ components
  [ ] API contract: @neurex/contracts up-to-date

Deployment:
  [ ] Docker image builds (next:14)
  [ ] CI/CD passes (GitHub Actions)
  [ ] Staging deploy works
  [ ] No blockers for main branch
```

**Subtasks:**
1. Run full audit (tsc, eslint, jest, lighthouse, accessibility)
2. Document findings in FAZA_0_COMPLETION_REPORT.md
3. Create approval checklist for CTO

**Acceptance Criteria:**
- [ ] All checklist items ✅
- [ ] FAZA_0_COMPLETION_REPORT.md signed off
- [ ] Ready for production deployment

---

#### Task 12.2: Retrospective + Handoff Documentation
```
Goal: Document learnings + next phase (FAZA 1)
```

**Subtasks:**
1. Team retro (1h):
   - What went well? (hook split efficiency, type safety)
   - What was hard? (query key migration, responsive design)
   - What to improve? (earlier testing, smaller PRs)

2. Create FAZA_0_RETROSPECTIVE.md:
   ```markdown
   # FAZA 0 Retrospective (3 hafta)
   
   ## By Numbers
   - 4 kritik bulgu: 100% fixed
   - 5 blocking bulgu: 100% fixed
   - Code: 2835 → 400 (new-project), 2604 → 1800 (use-mgmt), 882 → 200 (AppShell)
   - Tests: +50 unit, +8 E2E
   - Coverage: 45% → 65%
   - TypeScript: 40 → 0 error
   - Bundle: 650KB → 480KB
   - Lighthouse: 65 → 88
   
   ## Key Learnings
   1. Component split first → test easier
   2. Type contracts (@neurex/contracts) unblock frontend + backend
   3. Query key factory prevents bugs (no duplicate fetches)
   4. Responsive done upfront → fewer late fixes
   5. E2E tests catch integration bugs early
   
   ## FAZA 1 Focus (6 hafta, 32 bulgu yüksek-risk)
   1. Dashboard virtualization (performance)
   2. Mobile-first responsive (5 pages)
   3. Form UX improvements (20 forms)
   4. Notification system (realtime)
   5. Dark mode support
   ```

3. Create FAZA_1_PLAN.md:
   ```markdown
   # FAZA 1 Plan (6 hafta)
   
   ## Sprint 4 (Mon 7/7 - Fri 7/11): Dashboard + Performance
   - Virtual scrolling (50 widgets)
   - Lazy load charts
   - Memoization audit (React.memo missing)
   - Bundle optimization (code split routes)
   
   ## Sprint 5 (Mon 7/14 - Fri 7/18): Mobile Responsive Finish
   - Case, Run, Defect responsive complete
   - Tab/accordion patterns
   - Touch interactions
   
   ## Sprint 6 (Mon 7/21 - Fri 7/25): Forms + UX Polish
   - Form error UX (inline validation)
   - Empty states (20+ pages)
   - Loading skeletons
   - Dark mode
   ```

**Acceptance Criteria:**
- [ ] Retro documented
- [ ] FAZA_0_RETROSPECTIVE.md merged
- [ ] FAZA_1_PLAN.md ready for planning

---

## Resource Allocation (Sprint 3)

| Role | Name | Task | Days |
|------|------|------|------|
| Dev A | — | 9.1-9.4 (responsive pages) | 4 days |
| Dev B | — | 10.1-10.2 (dashboard responsive, Lighthouse) | 4 days |
| Dev + QA | — | 11.1-11.2 (E2E tests) | 4 days |
| All | — | 12.1-12.2 (quality gate, retro) | 2 days |

---

## Dependencies (Sprint 3)

```
Task 9.1-9.4 (responsive refactor)
  └─ DEPENDS ON Sprint 1-2 completion
  └─ NO EXTERNAL DEPENDENCY (parallel)

Task 10.1-10.2 (dashboard + Lighthouse)
  └─ DEPENDS ON Task 9.1-9.4 (responsive base)
  └─ DEPENDS ON image/code split optimization

Task 11.1-11.2 (E2E tests)
  └─ DEPENDS ON Task 9.1-9.4 (pages responsive)
  └─ DEPENDS ON test data seed (database)

Task 12.1-12.2 (quality gate + retro)
  └─ DEPENDS ON All above tasks
```

---

## Success Criteria (Sprint 3)

### Code Quality (Final)
- [ ] TypeScript: 0 error (100% pass)
- [ ] Linter: 0 violation
- [ ] Bundle: <500KB (gzip)
- [ ] Code coverage: ≥80% (critical paths)

### Performance (Final)
- [ ] Lighthouse: ≥85 (all pages)
- [ ] LCP: <1.5s
- [ ] TTI: <1.5s
- [ ] No memory leaks (DevTools profiling)

### Testing (Final)
- [ ] Unit tests: 200+ pass
- [ ] E2E tests: 8 pass (5 happy + 3 error)
- [ ] 0 regression from baseline
- [ ] Coverage report: 80%+ critical paths

### Accessibility (Final)
- [ ] WCAG AA: 0 violations
- [ ] Touch targets: ≥48px
- [ ] Color contrast: ≥4.5:1

### Documentation (Final)
- [ ] ADR-0015 merged
- [ ] Component storybook updated
- [ ] FAZA_0_COMPLETION_REPORT.md signed off
- [ ] FAZA_1_PLAN.md ready

---

## Risk & Mitigation (Sprint 3)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Responsive design cascades | Medium | Medium | Prioritize critical pages (new-project, case, run) |
| Lighthouse optimization premature | Low | Medium | Measure baseline first, then optimize (Task 10.2) |
| E2E test flakiness | Medium | Medium | Use explicit waits, avoid sleep(), retry logic |
| Quality gate deadline | Low | Low | Extend by 2-3 days if needed (flexible end date) |

---

---

# SUMMARY TABLE

## 3-Sprint Overview

| Sprint | Theme | Key Tasks | FTE | Days | Success Metric |
|--------|-------|-----------|-----|------|-----------------|
| **1** | Mega-Component Split + Type Foundation | new-project split, @neurex/contracts, AppShell start, TS baseline | 3-4 | 5 | 0 TS error, new-project testable, contract imports work |
| **2** | Hook Monolith Split + Query Consistency | use-management 6-way split, query keys 100%, form validation, TS strict | 3-4 | 5 | Bundle -50KB, 20 forms Zod, TS 40→5 errors, 0 circular deps |
| **3** | Responsive + E2E + Quality Gate | 5 pages responsive, Lighthouse ≥85, E2E 8 tests, quality gate pass | 3-4 | 5 | Bundle <500KB, Lighthouse ≥85, 8 E2E pass, production-ready |

## By Numbers

| Metric | Start | End | Change |
|--------|-------|-----|--------|
| **Code Size** | | | |
| new-project.tsx | 2835 | <400 | -2435 (-86%) |
| use-management.ts | 2604 | ~400×6 | -2000 (-77%) |
| AppShell.tsx | 882 | <200 | -682 (-77%) |
| **Quality** | | | |
| TypeScript errors | 40 | 0 | -40 (-100%) |
| Linter violations | 50+ | 0 | -50+ (-100%) |
| Bundle size | 650KB | <500KB | -150KB (-23%) |
| **Testing** | | | |
| Unit tests | 100 | 200+ | +100 (+100%) |
| E2E tests | 0 | 8 | +8 (+∞) |
| Coverage | 45% | 80%+ | +35% |
| **Performance** | | | |
| Lighthouse | 65 | ≥85 | +20 (+31%) |
| LCP | 3.2s | <1.5s | -1.7s (-53%) |
| TTI | 3.2s | <1.5s | -1.7s (-53%) |

## Resource Investment

- **Total FTE:** ~10-12 FTE-days (3 devs × 5 days = 15 dev-days, 1 designer, 1 QA)
- **Cost:** ~$45K-$50K (assuming $3.5K/dev-day, $2.5K designer/QA-day)
- **Timeline:** 3 hafta (18 güngün) — aggressive but achievable with dedicated team

## Go/No-Go Criteria (Gate End of Sprint 3)

| Criteria | Threshold | Status |
|----------|-----------|--------|
| TypeScript errors | 0 | **MUST PASS** |
| Linter violations | 0 | **MUST PASS** |
| Bundle size | <500KB | **MUST PASS** |
| Lighthouse (avg) | ≥85 | **MUST PASS** |
| E2E critical paths | 5/5 pass | **MUST PASS** |
| Code review issues | <5 major | **SHOULD PASS** |
| Security audit | 0 critical | **MUST PASS** |

**If all criteria pass:** → Production deployment ✅
**If any MUST PASS fail:** → Extend Sprint 3 by 1-2 hafta + remediation

---

## Next Steps (Start of Sprint 1)

1. **Team alignment** (30 min):
   - CTO/Product approve 4 kritik + 5 blocking
   - Assign Dev A, B, C, Designer, QA
   - Kickoff meeting (overview + dependencies)

2. **Environment setup** (1h):
   - Clone feature branch: `git checkout -b feature/frontend-refactor`
   - Install dependencies: `npm install`
   - Run baseline tests: `npm test` (establish baseline)
   - Measure baseline metrics (Lighthouse, bundle, tsc errors)

3. **Daily standup** (10 min):
   - What's done?
   - What's blocked?
   - Risk escalation?

4. **Weekly review** (1h):
   - Demo work (new-project split, hooks working, responsive page)
   - Metrics update (coverage, bundle, errors)
   - Adjust plan if needed (scope creep, dependencies)

---

**Created:** 2026-06-09
**Plan Status:** Ready for approval
**Timeline:** 3 hafta (Mon 6/16 - Fri 7/4)
**Confidence:** High (80% based on similar refactors)
