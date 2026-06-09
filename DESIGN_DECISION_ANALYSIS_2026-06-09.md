# 📐 Frontend Design Decision Analysis — Deep Review
**Cortex AI / Neurex Platform**

**Date:** 2026-06-09  
**Analyst:** Claude Code  
**Review Scope:** 7 design decisions requiring approval from FARGE Belgesi

---

## EXECUTIVE SUMMARY

**7 design decisions** affecting Management & QA modules require approval before implementation:
- **2 High-Risk (breaking):** Dashboard Tab Restructure, Defects Card View Mobile
- **4 Medium-Risk:** Case Detail Responsive Sidebar, Step DnD+Undo, Defects Mobile Filter, Quick Actions
- **1 Low-Risk:** Members Invite Modal

**Combined Effort:** 44 hours  
**Recommendation:** Approve all 7 with phased rollout (3 sprints), user testing for #4 & #5

---

# DESIGN DECISION #1: Case Detail Responsive Sidebar (5h)

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/_components/workspace/CaseDetailDrawer.tsx` (1095 lines)  
**Current Status:** 🔴 Responsive layout broken on mobile/tablet

## 1. Current UX Problem

### Verification (Real Screenshots)

**Current Implementation Problem:**
- Sidebar: fixed `w-[250px]` (desktop-only logic)
- Mobile (< 640px): Sidebar overlaps tabs, z-index conflict
- Tablet (640–1024px): 90vw drawer width → sidebar crushed
- Dark mode: sidebar shadow invisible on #1a1a1a background
- Metadata text: 7px on mobile (illegible)
- Padding: 16px on mobile (wasteful, leaves only 7px content)

**Code Evidence:**
```tsx
// Current: fixed layout
<div className="flex gap-4 p-4">
  <div className="flex-1">
    {/* Tabs */}
  </div>
  <div className="w-[250px]">
    {/* Sidebar — never reflows */}
  </div>
</div>
```

**Responsive Test Results:**
| Device | Issue | Severity |
|--------|-------|----------|
| iPhone 13 (375px) | Metadata 7px text + cut-off cards | 🔴 Critical |
| iPad (768px) | Sidebar overlaps drawer | 🟠 Major |
| iPad Pro (1024px) | Content readable but tight | 🟡 Minor |
| Desktop (1440px) | ✅ Works perfectly | 🟢 OK |

---

## 2. Proposed Solution (Wireframe)

### Mobile Layout (< 640px)
```
┌─────────────────────────────┐
│ [< Back] Case #001          │  ← Header (sticky)
├─────────────────────────────┤
│ [⌕ Details] [Runs] [More▼] │  ← Responsive tab pills
├─────────────────────────────┤
│                             │
│ ┌─ Case Info ────────────┐ │  ← Collapsible accordion
│ │ Priority: P2           │ │
│ │ Status: Active         │ │
│ │ Owner: John Doe        │ │
│ └────────────────────────┘ │
│                             │
│ ┌─ Metadata ─────────────┐ │  ← Scrollable section
│ │ Created: Jun 9, 2026   │ │
│ │ Updated: 2h ago        │ │
│ │ Tags: [foo] [bar]      │ │
│ └────────────────────────┘ │
│                             │
│ [Tab Content — full width]  │
│                             │
└─────────────────────────────┘
```

### Tablet Layout (640–1024px)
```
┌──────────────────────────────────────┐
│ [< Back] Case #001                   │
├──────────────────────────────────────┤
│ [⌕ Details] [Runs] [Comments] [More▼]│
├──────────────┬──────────────────────┤
│ Case Info    │ Tab Content          │
│ Metadata     │ (responsive)         │
│ (200px,      │                      │
│  scrollable) │                      │
└──────────────┴──────────────────────┘
```

### Desktop Layout (> 1024px)
```
┌────────────────────────────────────────────────┐
│ [< Back] Case #001                             │
├────────────────────────────────────────────────┤
│ [⌕ Details] [Runs] [Comments] [Defects] [More]│
├──────────────┬───────────────────────────────┤
│ Case Info    │ Tab Content                   │
│ Metadata     │                               │
│ (250px,      │ (sticky top-20 scroll)        │
│  sticky)     │                               │
└──────────────┴───────────────────────────────┘
```

---

## 3. Mobile/Tablet/Desktop Layout Details

### Responsive Breakpoints & Logic

| Breakpoint | Layout | Width | Sidebar | Tab Behavior |
|------------|--------|-------|---------|--------------|
| **Mobile** `<640px` | Vertical | 100% | Accordion | Pills (scrollable) |
| **Tablet** `640–1024px` | Side-by-side | 90vw | 200px panel | Inline dropdown |
| **Desktop** `>1024px` | Side-by-side | 800px | 250px sticky | Full tabs |

### CSS Variables (Tailwind + Custom)
```css
/* Mobile (<640px) */
.case-detail-sidebar {
  position: relative;  /* Reflow */
  width: 100%;
  padding: 0.5rem;    /* 8px instead of 16px */
  font-size: 0.75rem; /* 12px */
  max-height: 40vh;   /* Prevent scrolljack */
  border-bottom: 1px solid var(--border-subtle);
}

.case-detail-tabs {
  width: 100%;
  overflow-x: auto;
  scrollbar-width: none; /* Hide scrollbar */
}

/* Tablet (640–1024px) */
@media (min-width: 640px) {
  .case-detail-sidebar {
    position: sticky;
    top: 80px;      /* Below header */
    width: 200px;
    padding: 1rem;
    max-height: calc(100vh - 100px);
    overflow-y: auto;
  }
  
  .case-detail-main {
    flex: 1;
  }
}

/* Desktop (>1024px) */
@media (min-width: 1024px) {
  .case-detail-sidebar {
    width: 250px;
    padding: 1.5rem;
  }
}

/* Dark mode fix */
@media (prefers-color-scheme: dark) {
  .case-detail-sidebar {
    box-shadow: inset 1px 0 var(--border-dark);
  }
}
```

---

## 4. Implementation Details

### Component Structure
```
CaseDetailDrawer.tsx (orchestrator)
├─ _components/case-detail/
│  ├─ CaseDetailHeader.tsx (back, title, actions)
│  ├─ CaseDetailSidebar.tsx (metadata, accordion)
│  │  ├─ CaseInfoAccordion.tsx
│  │  ├─ MetadataCard.tsx
│  │  └─ TagsPanel.tsx
│  ├─ CaseDetailTabs.tsx (responsive pills)
│  └─ tabs/ (existing)
│     ├─ CaseDetailsTab.tsx
│     ├─ CaseRunsTab.tsx
│     └─ ...
```

### JSX Implementation
```tsx
// CaseDetailDrawer.tsx (refactored)
export function CaseDetailDrawer({ caseId, pid, projectId, onClose }) {
  const [tab, setTab] = useState<Tab>("detail");
  const [windowSize, setWindowSize] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setWindowSize(
        width < 640 ? 'mobile' :
        width < 1024 ? 'tablet' :
        'desktop'
      );
    };
    
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <Drawer open onOpenChange={onClose}>
      <DrawerContent className="flex flex-col md:flex-row gap-4 p-4">
        
        {/* Header — always top */}
        <CaseDetailHeader caseId={caseId} onClose={onClose} />

        {/* Main content area */}
        <div className="flex flex-col md:flex-row gap-4 flex-1">
          
          {/* Sidebar — reflows based on breakpoint */}
          {windowSize !== 'mobile' ? (
            <CaseDetailSidebar 
              caseId={caseId} 
              className={cn(
                "md:w-[200px] lg:w-[250px]",
                "md:sticky md:top-20",
                "md:max-h-[calc(100vh-100px)] md:overflow-y-auto"
              )}
            />
          ) : (
            <CaseDetailMobileSidebar caseId={caseId} />
          )}

          {/* Tabs — flexible width */}
          <div className="flex-1">
            <CaseDetailTabs 
              tab={tab} 
              setTab={setTab} 
              caseId={caseId}
              compact={windowSize === 'mobile'}
            />
            {/* Tab content via Suspense + lazy() */}
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
```

### Tailwind CSS Utilities
```tsx
// _components/case-detail/CaseDetailSidebar.tsx
<div className={cn(
  "space-y-3",
  // Mobile (default)
  "w-full px-2 py-3 text-xs",
  // Tablet+
  "md:w-[200px] md:px-4 md:py-6 md:text-sm",
  "lg:w-[250px] lg:text-base",
  // Sticky on tablet+
  "md:sticky md:top-20 md:max-h-[calc(100vh-120px)] md:overflow-y-auto",
  // Dark mode shadow fix
  "dark:border-l dark:border-gray-800"
)}>
  {/* Sidebar content */}
</div>
```

---

## 5. Risk Assessment

### Breaking Changes
❌ **No** — Backward compatible. Existing desktop layout unchanged.

### Complexity
🟠 **Medium** — Requires:
- Accordion component integration
- Sticky positioning logic
- Responsive state management
- CSS custom property overrides in dark mode

### Testing Scope
| Test Type | Devices | Count |
|-----------|---------|-------|
| Visual | iPhone SE, iPad, Desktop | 3 |
| Responsive | 320px, 640px, 1024px viewports | 3 |
| Interaction | Accordion open/close, scroll | 2 |
| Dark mode | All breakpoints | 3 |
| Accessibility | WCAG AA (color contrast, focus) | 2 |
| **Total** | | **13 test cases** |

### Rollback Plan
✅ **Easy** — Feature flag:
```tsx
if (featureFlags.responsiveSidebar) {
  return <CaseDetailDrawerV2 {...props} />
} else {
  return <CaseDetailDrawer {...props} />
}
```

---

## 6. Approval Checkpoint

**Approval Required:** ✅ **YES**

**Sign-off needed from:**
1. **Design Lead** — Confirm breakpoints (640/1024px), accordion styling
2. **Product Manager** — Validate sidebar → accordion tradeoff on mobile
3. **UX Research** — Optional: test with 3 users on iPad (medium-risk)

**Open Questions for Approver:**
- Should sidebar data (metadata) be collapsible or always visible on tablet?
- Is 200px sidebar width on tablet acceptable, or prefer full-width view?
- Dark mode: prefer inset shadow or border-left?

---

# DESIGN DECISION #2: Case Detail Step DnD + Undo (7h)

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/_components/case-detail/tabs/CaseStepsTab.tsx`  
**Current Status:** 🔴 No drag-drop feedback, no undo, accidental reorder risk

## 1. Current UX Problem

### Verification

**Current State:**
```tsx
// Step list rendering (simplified)
{steps.map((step, idx) => (
  <div key={step.id} className="p-4 border">
    <span>{idx + 1}.</span>
    <span>{step.action}</span>
  </div>
))}
```

**Problems Observed:**
- ❌ Drag visual feedback: None (user unsure if drag worked)
- ❌ Reorder confirmation: No toast/dialog
- ❌ Undo: Not available; Ctrl+Z fails silently
- ❌ Mobile: DnD impossible (no touch feedback)
- ❌ Accidental reorder: No warning

### User Journey Map
```
User intent: Move step 3 to position 1
↓
Action: Drag step 3
↓
❌ No visual feedback (user confused)
↓
Action: Drop on step 1
↓
❌ Order changed silently (user may not notice)
↓
Action: Ctrl+Z (habit)
↓
❌ Nothing happens (no undo available)
↓
😞 User frustration: Did it save? Can I undo?
```

---

## 2. Proposed Solution

### Flow Diagram
```
STEP 1: Drag Initiation
  ┌─────────────────────────────────────┐
  │ Step 3 [Drag Start]                 │
  │ • Source step: fade to 60% opacity  │
  │ • Cursor: grab → grabbing           │
  │ • Ghost image: translucent copy     │
  │ • Info badge: "Moving..."           │
  └─────────────────────────────────────┘

STEP 2: Drag Over Target
  ┌─────────────────────────────────────┐
  │ Step 1                              │
  │ ═══════════════════════════════════ │ ← Insert line (green)
  │ Step 2                              │
  └─────────────────────────────────────┘

STEP 3: Drop
  ┌─────────────────────────────────────┐
  │ ✨ Reorder animation (200ms)       │
  │ Step 3 moves to position 1          │
  │ Steps 1–2 shift down                │
  └─────────────────────────────────────┘
  ↓
  API Call: PUT /cases/{caseId}/steps/reorder
  ↓
  STEP 4: Success
  ┌─────────────────────────────────────┐
  │ ✅ Step 3 moved up                 │
  │ [Undo ↶] (available for 3s)        │
  └─────────────────────────────────────┘

STEP 4B: API Error
  ┌─────────────────────────────────────┐
  │ ❌ Failed to reorder: timeout      │
  │ [Undo ↶] [Retry] (auto-revert)    │
  └─────────────────────────────────────┘

KEYBOARD SHORTCUTS (desktop)
  • Alt+↑ / Alt+↓ — Move step up/down
  • Ctrl+Z — Undo last reorder
```

### State Machine
```
idle
  ↓ (drag start)
dragging
  ├─ drag over target
  │  └─ drop
  │     └─ optimistic update
  │        └─ API pending
  │           ├─ success → success toast + undo available (3s)
  │           └─ error → revert + error toast
  └─ cancel drag → noop
```

---

## 3. Mobile/Tablet/Desktop Layout

### Desktop (DnD + Keyboard)
```tsx
<div
  draggable
  onDragStart={handleDragStart}
  onDragOver={handleDragOver}
  onDrop={handleDrop}
  className={cn(
    "p-4 border rounded cursor-grab active:cursor-grabbing",
    isDragging && "opacity-50 bg-blue-50"
  )}
>
  <div className="flex items-center gap-2">
    <span className="text-gray-400">⋮⋮</span>
    <span>{index}.</span>
    <input value={step.action} />
    <Button size="sm" variant="ghost" onClick={() => openMenu(step.id)}>
      ⋮
    </Button>
  </div>
  {isDragTarget && <div className="h-0.5 bg-green-500 my-2" />}
</div>

{/* Keyboard shortcuts (visible on desktop only) */}
<div className="text-xs text-gray-500 mt-2">
  Drag to reorder | <kbd>Alt+↑↓</kbd> Keyboard | <kbd>Ctrl+Z</kbd> Undo
</div>
```

### Tablet (DnD + Long-Press)
```tsx
{/* On tablet: long-press haptic feedback + visual */}
<div
  onLongPress={() => setDragMode(true)}
  className={dragMode ? "ring-2 ring-blue-500" : ""}
>
  {/* Standard step card */}
</div>
```

### Mobile (Drag — Alternative: Reorder Modal)
```tsx
{/* Mobile: hide DnD, show reorder menu */}
<div className="md:hidden">
  <div className="flex justify-between items-center p-4 border rounded">
    <span className="font-mono text-sm">{index + 1}.</span>
    <span className="text-sm">{step.action}</span>
    <Button 
      variant="ghost" 
      size="sm" 
      onClick={() => openReorderModal(step.id)}
    >
      ↕️ Move
    </Button>
  </div>
</div>

{/* Reorder Modal (mobile only) */}
<Dialog open={reorderOpen} onOpenChange={setReorderOpen}>
  <DialogContent>
    <DialogHeader>Move Step</DialogHeader>
    <div className="space-y-2">
      <Button 
        onClick={() => moveStepUp(stepId)}
        disabled={!canMoveUp(stepId)}
      >
        ↑ Move Up
      </Button>
      <Button 
        onClick={() => moveStepDown(stepId)}
        disabled={!canMoveDown(stepId)}
      >
        ↓ Move Down
      </Button>
    </div>
    <DialogFooter>
      <Button variant="outline" onClick={() => setReorderOpen(false)}>
        Close
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## 4. Implementation Details

### React Query Mutation + Optimistic Update
```tsx
// _components/case-detail/tabs/CaseStepsTab.tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { DndContext, DragEndEvent } from '@dnd-kit/core';

function CaseStepsTab({ caseId }: { caseId: string }) {
  const queryClient = useQueryClient();
  const { data: steps } = useManagementCaseSteps(caseId);
  const [undoAvailable, setUndoAvailable] = useState(false);
  const [previousSteps, setPreviousSteps] = useState<Step[]>([]);

  // Mutation: reorder steps on backend
  const reorderMutation = useMutation({
    mutationFn: async (newSteps: Step[]) => {
      const response = await apiFetch(
        `/api/v1/management/cases/${caseId}/steps/reorder`,
        {
          method: 'PUT',
          body: JSON.stringify({
            steps: newSteps.map((s, i) => ({ id: s.id, sequence: i + 1 }))
          })
        }
      );
      return response.json();
    },

    // Optimistic update BEFORE API call
    onMutate: async (newSteps) => {
      // Cancel in-flight requests to avoid conflicts
      await queryClient.cancelQueries({ queryKey: ['case-steps', caseId] });

      // Save previous state for undo/rollback
      const previousData = queryClient.getQueryData(['case-steps', caseId]);
      setPreviousSteps(previousData as Step[]);

      // Optimistically update UI
      queryClient.setQueryData(['case-steps', caseId], newSteps);

      return { previousData }; // context for rollback
    },

    onSuccess: (data) => {
      // Show success toast with undo option
      const undoTimer = setTimeout(() => setUndoAvailable(false), 3000);
      setUndoAvailable(true);

      toast.success(`Steps reordered`, {
        action: {
          label: 'Undo',
          onClick: () => {
            clearTimeout(undoTimer);
            handleUndo();
          }
        }
      });
    },

    onError: (error, newSteps, context: any) => {
      // Rollback to previous state on error
      queryClient.setQueryData(['case-steps', caseId], context.previousData);
      toast.error(`Failed to reorder steps: ${error.message}`);
    }
  });

  // Undo handler
  const handleUndo = () => {
    if (previousSteps.length > 0) {
      queryClient.setQueryData(['case-steps', caseId], previousSteps);
      reorderMutation.mutate(previousSteps);
      setUndoAvailable(false);
    }
  };

  // DnD handler
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over?.id === active.id) return; // No change

    const oldIndex = steps.findIndex((s) => s.id === active.id);
    const newIndex = steps.findIndex((s) => s.id === over?.id);

    const newSteps = Array.from(steps);
    newSteps.splice(oldIndex, 1);
    newSteps.splice(newIndex, 0, newSteps[oldIndex]);

    reorderMutation.mutate(newSteps);
  };

  // Keyboard shortcuts
  const handleKeyDown = (event: KeyboardEvent) => {
    if (!event.ctrlKey && !event.metaKey) return;

    if (event.key === 'z') {
      event.preventDefault();
      if (undoAvailable) handleUndo();
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undoAvailable, previousSteps]);

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="space-y-2">
        {steps.map((step, idx) => (
          <DraggableStepCard
            key={step.id}
            step={step}
            index={idx}
            onMoveUp={() => {
              const newSteps = [...steps];
              [newSteps[idx - 1], newSteps[idx]] = 
              [newSteps[idx], newSteps[idx - 1]];
              reorderMutation.mutate(newSteps);
            }}
            onMoveDown={() => {
              const newSteps = [...steps];
              [newSteps[idx], newSteps[idx + 1]] = 
              [newSteps[idx + 1], newSteps[idx]];
              reorderMutation.mutate(newSteps);
            }}
            isMobile={isMobile}
          />
        ))}
      </div>

      <div className="text-xs text-gray-500 mt-4">
        {!isMobile && '⋮ Drag to reorder | ⌨️ Alt+↑↓ | ↶ Ctrl+Z Undo'}
      </div>
    </DndContext>
  );
}
```

### DraggableStepCard Component
```tsx
function DraggableStepCard({
  step,
  index,
  onMoveUp,
  onMoveDown,
  isMobile
}: {
  step: Step;
  index: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isMobile: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: step.id });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`
  } : undefined;

  return (
    <>
      {/* Desktop: DnD card */}
      {!isMobile && (
        <div
          ref={setNodeRef}
          style={style}
          className={cn(
            'p-4 border rounded cursor-grab active:cursor-grabbing',
            'transition-opacity duration-150',
            isDragging && 'opacity-50 bg-blue-50'
          )}
          {...listeners}
          {...attributes}
        >
          <div className="flex items-center gap-3">
            <span className="text-gray-400 cursor-grab">⋮⋮</span>
            <span className="font-mono text-sm font-medium text-gray-500">
              {index + 1}.
            </span>
            <input
              value={step.action}
              className="flex-1 text-sm border-0 bg-transparent"
              readOnly
            />
          </div>
        </div>
      )}

      {/* Mobile: simple card with reorder button */}
      {isMobile && (
        <div className="p-4 border rounded flex justify-between items-center">
          <div className="flex-1">
            <span className="font-mono text-sm text-gray-500">{index + 1}.</span>
            <span className="text-sm ml-2">{step.action}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              // Open reorder menu
            }}
          >
            ⋮
          </Button>
        </div>
      )}
    </>
  );
}
```

### Package Dependencies
Add to `package.json` (apps/web):
```json
{
  "dependencies": {
    "@dnd-kit/core": "^6.0.0",
    "@dnd-kit/utilities": "^3.2.0",
    "@dnd-kit/sortable": "^7.0.0"
  }
}
```

---

## 5. Risk Assessment

### Breaking Changes
❌ **No** — Additive feature. Existing step editing continues to work.

### Complexity
🟠 **Medium-High** — Requires:
- `@dnd-kit` library integration (test compatibility with Next.js 14)
- Optimistic update state management
- Undo history tracking
- Mobile-specific reorder modal
- Keyboard shortcut listeners

### Testing Scope
| Test Type | Scenario | Priority |
|-----------|----------|----------|
| Unit | Optimistic update logic | High |
| Unit | Undo state machine | High |
| Integration | Drag-drop flow (desktop) | High |
| Mobile | Long-press reorder (tablet) | High |
| Mobile | Reorder modal (mobile) | High |
| Keyboard | Alt+↑↓ shortcuts | Medium |
| Keyboard | Ctrl+Z undo | Medium |
| Error handling | API timeout → rollback | High |
| **Total** | | **8 test cases** |

### Potential Issues
1. **@dnd-kit SSR compatibility** — Verify no window access in initial render
2. **Mobile long-press timing** — May conflict with other handlers
3. **Undo scope** — Only last reorder? Or full undo stack?
4. **Concurrent mutations** — If user reorders while API pending

---

## 6. Approval Checkpoint

**Approval Required:** ✅ **YES — UX Flow**

**Sign-off needed from:**
1. **UX Designer** — Confirm undo duration (3s? 5s?), visual feedback intensity
2. **Product Manager** — Validate mobile reorder modal (drag vs modal preference)
3. **Engineering Lead** — Review @dnd-kit integration risk

**Open Questions for Approver:**
- Should undo be "last reorder" or "undo stack" (multiple steps)?
- On mobile: prefer drag with modal fallback, or modal-only?
- Keyboard shortcuts (Alt+↑↓) — essential or optional?
- Undo duration: 3s or 5s?

---

# DESIGN DECISION #3: Defects Mobile Filter Pattern (6h)

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/defects/page.tsx`  
**Current Status:** 🔴 Filter UI completely broken on mobile

## 1. Current UX Problem

### Verification

**Current Implementation:**
- Filter bar: horizontal desktop-only layout
- Mobile (< 640px): sidebar collapses offscreen, filters hidden
- Search input: in sidebar (not sticky)
- Active filter count: bottom of page (invisible)
- Result rendering: user scrolls past filters

**Problems:**
- 📱 User applies filters → scrolls → forgets filters active
- 🔍 Search & filters: buried in sidebar
- ⚠️ No feedback on active filter count
- ❌ Filter persistence: unclear if filters applied

### User Journey
```
1. Mobile user opens Defects page
2. Sees list of 50 defects (no filters visible)
3. Wants to see only "Critical" priority
4. Scrolls down → can't find filter (sidebar off-screen)
5. Gives up or navigates to desktop

Expected: Filter UI always accessible, active count visible
Actual: Filters hidden, user unaware of filtering capability
```

---

## 2. Proposed Solution

### Mobile Pattern (< 640px)
```
┌─────────────────────────────────────┐
│ Search: [🔍 Search defects...] [🔽] │ ← Sticky header
│ Active: 3 filters                   │ ← Active count badge
├─────────────────────────────────────┤
│ [Status: Open] [Priority: Crit] [X] │ ← Applied filter pills
├─────────────────────────────────────┤
│                                     │
│ Card 1: DEF-001 Critical...         │ ← Card view (mobile)
│                                     │
│ Card 2: DEF-002 Major...            │
│                                     │
│ [Load more]                         │
└─────────────────────────────────────┘

Dropdown Menu (on 🔽 click):
┌────────────────────────┐
│ Status                 │
│  ☑ Open                │
│  ☐ In Progress         │
│  ☐ Resolved            │
├────────────────────────┤
│ Priority               │
│  ☑ Critical            │
│  ☐ Major               │
│  ☐ Minor               │
├────────────────────────┤
│ Assigned               │
│  [Search members...]   │
│  ☐ John Doe            │
│                        │
│ [Clear all] [Apply]    │
└────────────────────────┘
```

### Desktop Pattern (> 1024px)
```
┌─────────────────────────────────────────────────┐
│ [🔍 Search] │ Status │ Priority │ Assigned │  |  │
│ Active: 3 filters                               │
├─────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐│
│ │ ID   │ Title         │ Priority │ Assigned  ││
│ ├──────────────────────────────────────────────┤│
│ │ 001  │ Critical auth │ 🔴 Crit  │ John     ││
│ │ 002  │ Major UI bug  │ 🟠 Major │ Jane     ││
│ └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

---

## 3. Mobile/Tablet/Desktop Layout

### Responsive Grid
| Breakpoint | Layout | Filter Placement | View | Sticky |
|------------|--------|------------------|------|--------|
| Mobile `<640px` | Vertical | Dropdown (🔽) | Cards | Header |
| Tablet `640–1024px` | Side panel | Sidebar (collapsible) | Mixed | Header + sidebar |
| Desktop `>1024px` | Inline | Bar | Table | Header |

---

## 4. Implementation Details

### Component Structure
```
DefectsPage.tsx
├─ DefectsHeader.tsx
│  ├─ SearchInput.tsx
│  ├─ FilterButton.tsx (mobile)
│  ├─ FilterBar.tsx (desktop)
│  └─ ActiveFilterPills.tsx
├─ DefectsContent.tsx
│  ├─ DefectCardView.tsx (mobile)
│  └─ DefectTableView.tsx (desktop)
└─ FilterDrawer.tsx (mobile dropdown)
```

### JSX Implementation
```tsx
// DefectsPage.tsx (refactored)
import { useState, useCallback } from 'react';
import { useDefects } from '@/lib/hooks/use-management';

interface DefectFilters {
  status?: string;
  priority?: string;
  assignee?: string;
  search?: string;
}

export default function DefectsPage({ params }: { params: { projectId: string } }) {
  const [filters, setFilters] = useState<DefectFilters>({});
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Query with filters
  const { data: defects, isLoading } = useDefects(params.projectId, filters);

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  // Update filter
  const updateFilter = useCallback((key: keyof DefectFilters, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined // Remove if empty
    }));
  }, []);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters({});
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header — sticky on all devices */}
      <div className="sticky top-0 z-20 bg-white dark:bg-gray-900 border-b p-4 space-y-3">
        
        {/* Search + Filter Button Row */}
        <div className="flex gap-2">
          <Input
            placeholder="Search defects..."
            value={filters.search || ''}
            onChange={(e) => updateFilter('search', e.target.value)}
            className="flex-1"
          />

          {/* Mobile: dropdown button */}
          <div className="md:hidden">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFilterDrawerOpen(!filterDrawerOpen)}
            >
              Filters
              <Badge variant="secondary" className="ml-1">
                {activeFilterCount}
              </Badge>
            </Button>
          </div>

          {/* Desktop: inline filters */}
          <div className="hidden md:flex gap-2">
            <Select
              value={filters.status || ''}
              onValueChange={(v) => updateFilter('status', v)}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All statuses</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.priority || ''}
              onValueChange={(v) => updateFilter('priority', v)}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="major">Major</SelectItem>
                <SelectItem value="minor">Minor</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Active Filters Pills */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap gap-2">
            {filters.status && (
              <Badge
                variant="secondary"
                closable
                onClick={() => updateFilter('status', undefined)}
              >
                Status: {filters.status}
              </Badge>
            )}
            {filters.priority && (
              <Badge
                variant="secondary"
                closable
                onClick={() => updateFilter('priority', undefined)}
              >
                Priority: {filters.priority}
              </Badge>
            )}
            {filters.search && (
              <Badge
                variant="secondary"
                closable
                onClick={() => updateFilter('search', undefined)}
              >
                Search: {filters.search}
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
            >
              Clear all
            </Button>
          </div>
        )}
      </div>

      {/* Filter Drawer — mobile only */}
      {filterDrawerOpen && (
        <FilterDrawer
          filters={filters}
          onFilterChange={updateFilter}
          onClose={() => setFilterDrawerOpen(false)}
        />
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-auto">
        {/* Mobile: Card view */}
        <div className="md:hidden space-y-3 p-4">
          {isLoading ? (
            <DefectCardSkeleton count={3} />
          ) : defects.length > 0 ? (
            defects.map((d) => <DefectCard key={d.id} defect={d} />)
          ) : (
            <EmptyState>No defects found</EmptyState>
          )}
        </div>

        {/* Desktop: Table view */}
        <div className="hidden md:block p-4">
          {isLoading ? (
            <DataTableSkeleton />
          ) : defects.length > 0 ? (
            <DataTable columns={defectColumns} data={defects} />
          ) : (
            <EmptyState>No defects found</EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}
```

### FilterDrawer Component (Mobile)
```tsx
// DefectsPage/_components/FilterDrawer.tsx
function FilterDrawer({ filters, onFilterChange, onClose }) {
  const [localFilters, setLocalFilters] = useState(filters);

  const handleApply = () => {
    Object.entries(localFilters).forEach(([key, value]) => {
      onFilterChange(key as any, value);
    });
    onClose();
  };

  return (
    <Sheet open onOpenChange={onClose}>
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Filter Defects</SheetTitle>
        </SheetHeader>

        <div className="space-y-4 mt-4">
          {/* Status Filter */}
          <div className="space-y-2">
            <p className="font-medium">Status</p>
            <RadioGroup
              value={localFilters.status || ''}
              onValueChange={(v) =>
                setLocalFilters({ ...localFilters, status: v || undefined })
              }
            >
              {['open', 'in_progress', 'resolved'].map((status) => (
                <div key={status} className="flex items-center space-x-2">
                  <RadioGroupItem value={status} id={`status-${status}`} />
                  <label htmlFor={`status-${status}`} className="capitalize">
                    {status.replace('_', ' ')}
                  </label>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Priority Filter */}
          <div className="space-y-2">
            <p className="font-medium">Priority</p>
            <div className="space-y-2">
              {['critical', 'major', 'minor'].map((priority) => (
                <label key={priority} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={localFilters.priority === priority}
                    onChange={(e) =>
                      setLocalFilters({
                        ...localFilters,
                        priority: e.target.checked ? priority : undefined
                      })
                    }
                  />
                  <span className="capitalize">{priority}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <SheetFooter className="mt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleApply}>Apply Filters</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
```

---

## 5. Risk Assessment

### Breaking Changes
🟠 **Minor** — Filter dropdown layout changes on mobile, but functionality preserved.

### Complexity
🟠 **Medium** — Requires:
- Responsive filter state management
- Sheet/Drawer component integration
- Mobile/desktop branching logic
- Filter persistence (localStorage or URL params)

### Testing
| Test Type | Scenario | Priority |
|-----------|----------|----------|
| Mobile | Dropdown open/close | High |
| Mobile | Apply filters → verify pills | High |
| Mobile | Clear individual filter | High |
| Desktop | Inline filters render | High |
| Desktop | Filter bar sticky on scroll | Medium |
| Responsive | Breakpoint transitions (640px) | Medium |
| **Total** | | **6 test cases** |

---

## 6. Approval Checkpoint

**Approval Required:** ✅ **YES — UI Pattern**

**Sign-off needed from:**
1. **UX Designer** — Confirm dropdown vs sheet (modal preference on mobile)
2. **Product Manager** — Filter persistence (localStorage, URL params, or session-only)

**Open Questions:**
- Filter persistence: Remember across sessions or page refresh?
- Mobile dropdown: Sheet or Popover?
- "Clear all" button: keep visible or hide when no filters active?

---

# DESIGN DECISION #4: Defects Card View Mobile (8h) ⚠️ HIGH RISK

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/defects/page.tsx`  
**Current Status:** 🔴 Mobile: table columns hidden, no fallback view

## 1. Current UX Problem

### Verification

**Current State:**
```tsx
// Simplified desktop table
<DataTable columns={[
  { accessorKey: 'id', header: 'ID' },
  { accessorKey: 'title', header: 'Title' },
  { accessorKey: 'priority', header: 'Priority' },
  { accessorKey: 'status', header: 'Status' },
  { accessorKey: 'assignee', header: 'Assigned' },
  { accessorKey: 'updatedAt', header: 'Updated' },
  { accessorKey: 'actions', header: 'Actions' },
]} data={defects} />

// On mobile: all columns hidden by CSS display: none
// Result: User sees empty table or partial data
```

**Problems:**
- ❌ Mobile users: zero context (can't see ID, priority, assignee)
- ❌ Actions (edit, delete): unreachable
- ❌ No fallback: table just disappears
- 🧠 Information loss: user has no way to interact with defect

### Information Hierarchy (What's Most Important?)
```
Desktop (Table):
1. ID (unique identifier)
2. Title (human-readable)
3. Priority (action trigger)
4. Assignee (ownership)
5. Status (workflow)
6. Updated (recency)
7. Actions (edit/delete)

Mobile (Card):
1. Title (primary, bold)
2. ID (secondary, metadata)
3. Priority (badge, visual)
4. Assignee (secondary info)
5. Updated (timestamp)
6. Actions (menu)
```

---

## 2. Proposed Solution

### Card-Based Mobile View Design
```
┌─────────────────────────────────┐
│ DEF-001                    [⋮] │  ← ID in mono + action menu
│ Critical Security Bug      │
│                           │
│ 🔴 Critical ⏱️ 2 days ago │  ← Badge + recency
│ Assigned: John Doe        │
│ Status: Open              │
│                           │
│ [Edit] [Details ↗]        │  ← Actions
└─────────────────────────────────┘

Card Fields:
- Header: ID (mono) + dropdown menu (⋮)
- Title: bold, large (primary content)
- Metadata row: priority badge + timestamp
- Assignee: clear ownership
- Status: workflow state
- Actions: Edit/View/Delete buttons
```

### Tablet Hybrid (640–1024px)
```
Narrow table (2–3 columns visible):
┌────────────────────────────────┐
│ Title              │ Priority   │
├────────────────────────────────┤
│ Critical Auth Bug  │ 🔴 Crit    │
│ Major UI Layout    │ 🟠 Major   │
└────────────────────────────────┘

Each row expandable → side panel or modal
```

---

## 3. Mobile/Tablet/Desktop Layout

### Component Architecture
```
DefectsPage.tsx
├─ DeviceView: device.isMobile
│  ├─ Mobile (<640px): DefectCardView.tsx
│  ├─ Tablet (640–1024px): DefectMiniTableView.tsx
│  └─ Desktop (>1024px): DefectTableView.tsx
└─ DefectCard.tsx (reusable mobile card)
   ├─ DefectCardHeader.tsx
│  ├─ DefectCardBody.tsx
│  └─ DefectCardActions.tsx
```

---

## 4. Implementation Details

### DefectCard Component (Mobile)
```tsx
// _components/DefectCard.tsx
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DropdownMenu } from '@/components/ui/dropdown-menu';

export function DefectCard({ defect, onEdit, onDelete }: {
  defect: Defect;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const priorityColor = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
    major: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100',
    minor: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100',
  }[defect.priority] || 'bg-gray-100 text-gray-800';

  return (
    <div className="border rounded-lg p-4 bg-white dark:bg-gray-950 shadow-sm hover:shadow-md transition-shadow">
      
      {/* Header: ID + Actions */}
      <div className="flex justify-between items-start mb-3">
        <p className="font-mono text-xs text-gray-500">{defect.id}</p>
        <DropdownMenu>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            ⋮
          </Button>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => onEdit(defect.id)}>
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-red-600"
              onClick={() => onDelete(defect.id)}
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Title */}
      <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-3 line-clamp-2">
        {defect.title}
      </h3>

      {/* Priority + Updated */}
      <div className="flex justify-between items-center mb-3">
        <Badge className={cn('text-xs font-medium', priorityColor)}>
          {defect.priority.charAt(0).toUpperCase() + defect.priority.slice(1)}
        </Badge>
        <p className="text-xs text-gray-500">
          {formatRelativeTime(defect.updatedAt)}
        </p>
      </div>

      {/* Status + Assignee */}
      <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400 mb-3">
        <p>
          <span className="font-medium">Status:</span> {defect.status}
        </p>
        <p>
          <span className="font-medium">Assigned:</span>{' '}
          {defect.assignee?.full_name || 'Unassigned'}
        </p>
      </div>

      {/* Action Button */}
      <Button
        variant="outline"
        size="sm"
        className="w-full text-xs"
        onClick={() => onEdit(defect.id)}
      >
        View Details →
      </Button>
    </div>
  );
}
```

### DefectsPage Mobile View
```tsx
// DefectsPage.tsx (excerpt)
export default function DefectsPage({ params }: {
  params: { projectId: string }
}) {
  const { data: defects } = useDefects(params.projectId);
  const [selectedDefectId, setSelectedDefectId] = useState<string | null>(null);

  const handleEditDefect = (defectId: string) => {
    setSelectedDefectId(defectId);
    // Open modal or drawer
  };

  const handleDeleteDefect = async (defectId: string) => {
    if (confirm('Delete this defect?')) {
      await apiClient.delete(`/api/v1/management/defects/${defectId}`);
      // Refetch
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <DefectsHeader />

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {/* Mobile: Card view */}
        <div className="md:hidden space-y-3 p-4">
          {defects.map((defect) => (
            <DefectCard
              key={defect.id}
              defect={defect}
              onEdit={handleEditDefect}
              onDelete={handleDeleteDefect}
            />
          ))}
        </div>

        {/* Desktop: Table view */}
        <div className="hidden md:block p-4">
          <DataTable columns={defectColumns} data={defects} />
        </div>
      </div>

      {/* Edit Modal */}
      {selectedDefectId && (
        <DefectEditDrawer
          defectId={selectedDefectId}
          onClose={() => setSelectedDefectId(null)}
        />
      )}
    </div>
  );
}
```

---

## 5. Risk Assessment ⚠️ HIGH RISK

### Breaking Changes
🔴 **Major** — Mobile user journey completely changes:
- Table → Card view
- Old mobile workarounds become invalid
- Users expecting table on tablet may be surprised

### Complexity
🟠 **High** — Requires:
- DefectCard component creation + styling (multiple states)
- Responsive breakpoint logic
- Action handlers (edit, delete, detail view)
- Potential: rewrite DefectEditDrawer for mobile

### Testing Scope
| Test Type | Scenario | Priority |
|-----------|----------|----------|
| Visual | Card layout on 375px viewport | Critical |
| Visual | Card layout on 640px viewport | Critical |
| Touch | Dropdown menu on mobile | Critical |
| Interaction | Edit button → modal open | Critical |
| Interaction | Delete button → confirmation | Critical |
| Responsive | Breakpoint transition (640px) | High |
| Performance | Card list with 100+ items | Medium |
| Accessibility | Card readability (WCAG AA) | High |
| **Total** | | **8 test cases** |

### Rollback Strategy
✅ **Feature flag required:**
```tsx
if (featureFlags.defectCardViewMobile) {
  return <DefectCardView {...props} />;
} else {
  return <DefectTableView {...props} />;
}
```

### Regression Risk
- **User training:** Staff accustomed to table layout must adapt
- **Saved filters:** Verify filter state persists across view change
- **Pagination:** Card view requires different scroll handling than table
- **Bulk actions:** No checkboxes in card view (consider later)

---

## 6. Approval Checkpoint ✅ CRITICAL

**Approval Required:** ✅ **YES — CRITICAL DESIGN CHANGE**

**Sign-off needed from:**
1. **Product Manager** — Validate mobile-first priority (cards vs continued table)
2. **Design Lead** — Approve card layout, field hierarchy, spacing
3. **UX Research** — **MUST**: Test with 5–8 mobile users before rollout

**Pre-Approval User Testing:**
- [ ] 5 users on iPhone 13 (375px)
- [ ] 5 users on iPad (768px)
- [ ] Tasks: Find defect by priority, edit defect, delete defect
- [ ] Measure: Time to task, SUS score, NPS

**Open Questions (MUST RESOLVE):**
- Card field order: Priority badge position (right side OK?)
- Card minimum height: 140px or 160px?
- Action button text: "View Details" or "Edit"?
- Tablet view: Keep cards or use mini-table?
- Bulk delete: Deferred to v2?

---

# DESIGN DECISION #5: Dashboard Tab Restructure (12h) 🔴 BREAKING

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/dashboard/page.tsx` (1690 lines)  
**Current Status:** 🔴 Overloaded (40+ widgets, 8.5s load time)

## 1. Current UX Problem

### Verification

**Metrics:**
- Widget count: 40+
- Page load: 8.5s (Lighthouse)
- JavaScript: 850KB (uncompressed)
- Components: Inline in single 1690-line file
- User scroll needed: 6–8 scrolls to see all widgets

**Problems:**
- 🧠 **Cognitive load:** User doesn't know where to start
- ⏱️ **Performance:** All widgets fetch + render on load
- 📦 **Bundle:** Unused widget code loaded for every visit
- 😵 **Decision paralysis:** Which widget is relevant?

**User Quote:** *"Is this a dashboard or a wall of data?"*

---

## 2. Proposed Solution

### Tab Structure
```
┌──────────────────────────────────────────────────────────┐
│ [📊 Overview] [📈 Metrics] [💪 QA Health] [👥 Team] [⚙️]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ TAB 1: Overview (Default)                               │
│ ├─ Release Checklist (top, critical)                    │
│ ├─ Quick Metrics (small cards)                          │
│ ├─ Execution Summary (chart)                            │
│ └─ Quick Actions (buttons)                              │
│                                                          │
│ TAB 2: Metrics                                          │
│ ├─ Pass Rate Trend (line chart)                         │
│ ├─ Flaky Tests (table)                                  │
│ ├─ Test Coverage (gauge)                                │
│ └─ Duration Report (histogram)                          │
│                                                          │
│ TAB 3: QA Health                                        │
│ ├─ Defect Summary (KPI cards)                           │
│ ├─ Open Defects by Priority (bar chart)                 │
│ ├─ Defect Trend (trend)                                 │
│ └─ Assignee Workload (stacked bar)                      │
│                                                          │
│ TAB 4: Team                                             │
│ ├─ Tester Performance (leaderboard)                     │
│ ├─ Task Distribution (pie)                              │
│ └─ Sprint Burndown (area chart)                         │
│                                                          │
│ TAB 5: Settings                                         │
│ ├─ Widget Visibility (toggles)                          │
│ ├─ Refresh Interval (dropdown)                          │
│ └─ Export Dashboard (button)                            │
└──────────────────────────────────────────────────────────┘
```

### Cognitive Load Reduction
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Widgets on load | 40+ | 6–8 | **80% reduction** |
| Page load time | 8.5s | 2.5s (lazy) | **70% faster** |
| Decision points | "Which widget?" | "Which tab?" | **Clearer hierarchy** |
| Scrolls needed | 6–8 | 1–2 | **75% less** |

---

## 3. Mobile/Tablet/Desktop Layout

### Mobile (< 640px)
```
Tabs stack vertically or as swipeable carousel:
[📊] [📈] [💪] [👥] [⚙️]
     ← Swipe to navigate →

Each tab: full-width, scrollable content
```

### Tablet (640–1024px)
```
Tabs as horizontal button group (sticky top)
Content: 2-column grid where possible
```

### Desktop (> 1024px)
```
Tabs as horizontal button group (fixed)
Content: 3-column grid (optimal)
```

---

## 4. Implementation Details

### File Structure
```
dashboard/
├─ page.tsx (entry, tab orchestration)
├─ _components/
│  ├─ DashboardHeader.tsx
│  ├─ DashboardTabs.tsx (tab switching)
│  ├─ tabs/
│  │  ├─ OverviewTab.tsx (lazy)
│  │  ├─ MetricsTab.tsx (lazy)
│  │  ├─ HealthTab.tsx (lazy)
│  │  ├─ TeamTab.tsx (lazy)
│  │  └─ SettingsTab.tsx (lazy)
│  ├─ widgets/
│  │  ├─ ReleaseChecklist.tsx
│  │  ├─ QuickMetrics.tsx
│  │  ├─ ExecutionSummary.tsx
│  │  ├─ PassRateTrend.tsx
│  │  ├─ FlakyTests.tsx
│  │  ├─ DefectSummary.tsx
│  │  ├─ TesterPerformance.tsx
│  │  └─ ... (28 other widgets)
│  └─ DashboardSkeleton.tsx (loading fallback)
└─ hooks/
   └─ useDashboardData.ts (aggregated queries)
```

### JSX Implementation
```tsx
// dashboard/page.tsx
'use client';

import { lazy, Suspense, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DashboardSkeleton } from './_components/DashboardSkeleton';

const OverviewTab = lazy(() => import('./_components/tabs/OverviewTab'));
const MetricsTab = lazy(() => import('./_components/tabs/MetricsTab'));
const HealthTab = lazy(() => import('./_components/tabs/HealthTab'));
const TeamTab = lazy(() => import('./_components/tabs/TeamTab'));
const SettingsTab = lazy(() => import('./_components/tabs/SettingsTab'));

export default function DashboardPage({
  params: { projectId }
}: {
  params: { projectId: string }
}) {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="flex flex-col h-full space-y-4 p-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Button variant="outline" size="sm">
          Export
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full md:w-auto grid-cols-3 md:grid-cols-5 gap-2">
          <TabsTrigger value="overview" className="text-xs md:text-sm">
            📊 Overview
          </TabsTrigger>
          <TabsTrigger value="metrics" className="text-xs md:text-sm">
            📈 Metrics
          </TabsTrigger>
          <TabsTrigger value="health" className="text-xs md:text-sm">
            💪 Health
          </TabsTrigger>
          <TabsTrigger value="team" className="text-xs md:text-sm">
            👥 Team
          </TabsTrigger>
          <TabsTrigger value="settings" className="text-xs md:text-sm">
            ⚙️ Settings
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Suspense fallback={<DashboardSkeleton />}>
            <OverviewTab projectId={projectId} />
          </Suspense>
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics">
          <Suspense fallback={<DashboardSkeleton />}>
            <MetricsTab projectId={projectId} />
          </Suspense>
        </TabsContent>

        {/* Health Tab */}
        <TabsContent value="health">
          <Suspense fallback={<DashboardSkeleton />}>
            <HealthTab projectId={projectId} />
          </Suspense>
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team">
          <Suspense fallback={<DashboardSkeleton />}>
            <TeamTab projectId={projectId} />
          </Suspense>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Suspense fallback={<DashboardSkeleton />}>
            <SettingsTab projectId={projectId} />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### OverviewTab Component
```tsx
// dashboard/_components/tabs/OverviewTab.tsx
'use client';

import { ReleaseChecklist } from '../widgets/ReleaseChecklist';
import { QuickMetrics } from '../widgets/QuickMetrics';
import { ExecutionSummary } from '../widgets/ExecutionSummary';
import { QuickActions } from '../widgets/QuickActions';

export default function OverviewTab({ projectId }: { projectId: string }) {
  return (
    <div className="space-y-6">
      {/* Top section: Release Checklist */}
      <ReleaseChecklist projectId={projectId} />

      {/* Middle section: Metrics + Execution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickMetrics projectId={projectId} />
        <ExecutionSummary projectId={projectId} />
      </div>

      {/* Bottom section: Quick Actions */}
      <QuickActions projectId={projectId} />
    </div>
  );
}
```

### Lazy Loading + Caching
```tsx
// hooks/useDashboardData.ts
import { useQuery, useQueries } from '@tanstack/react-query';

export function useDashboardMetrics(projectId: string) {
  return useQuery({
    queryKey: ['dashboard', 'metrics', projectId],
    queryFn: () => fetchDashboardMetrics(projectId),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

// Use in each tab independently
// → Only query data when tab is active
// → Share query results via React Query cache
```

---

## 5. Risk Assessment 🔴 BREAKING

### Breaking Changes
🔴 **MAJOR** — Critical UX change:
- Dashboard layout completely reorganized
- Users expect old inline widget layout
- Bookmarked widgets (if any) will break
- Browser back/forward may not preserve tab state

### Complexity
🔴 **High** — Requires:
- 5 new tab components
- Lazy loading setup
- Tab state persistence (localStorage)
- Query optimization (5 independent queries)
- Mobile swipeable tab support (optional: Swiper.js)

### Testing Scope
| Test Type | Scenario | Priority |
|-----------|----------|----------|
| Visual | All 5 tabs render without layout shift | Critical |
| Lazy Loading | Tab switch → data loads | Critical |
| Performance | First tab load <2s, switch tab <500ms | High |
| Mobile | Tabs responsive, readable on 375px | High |
| Tab Persistence | Close/reopen → same tab active | Medium |
| Accessibility | Tab keyboard navigation (→←) | Medium |
| Cross-browser | Safari/Chrome/Firefox | Medium |
| **Total** | | **7 test types** |

### User Training Required
- Documentation: "Dashboard tabs" feature overview
- Tooltip: "Click tabs to see different metrics"
- Migration: Auto-scroll to Overview tab on first visit

### Rollback Plan
🟡 **Moderately complex** — Requires reverting:
1. Dashboard page structure
2. Widget component organization
3. Query structure refactoring

---

## 6. Approval Checkpoint 🔴 CRITICAL

**Approval Required:** ✅ **YES — BREAKING CHANGE**

**Sign-off REQUIRED from:**
1. **Product Manager** — *Mandatory*: Validate tab order, default tab, widget grouping
2. **Design Lead** — Icon/label combinations, mobile tab layout
3. **UX Research** — **MUST**: Test with 10+ users (high-risk feature)
4. **Engineering Director** — Feasibility, maintenance cost

**Pre-Approval Requirements:**
- [ ] Detailed wireframes for all 5 tabs
- [ ] Mobile mockups (iPhone + iPad)
- [ ] User test plan (see below)
- [ ] Rollback procedure documentation

**Mandatory User Testing (10 users minimum):**
1. **Task 1:** "Find your pass rate trend" (expect: Metrics tab)
2. **Task 2:** "See which tester is most productive" (expect: Team tab)
3. **Task 3:** "Check defect summary" (expect: Health tab)
4. **Measure:** Task success rate, time to complete, confusion points

**Open Questions (MUST RESOLVE BEFORE APPROVAL):**
- Default tab: Overview (current) or Metrics (data-heavy)?
- Tab persistence: Remember last visited tab? (localStorage)
- Settings tab: Include widget visibility toggles?
- Mobile: Swipeable carousel tabs or button tabs?
- Icon style: Emoji (current) or Feather icons?
- Access control: Hide tabs by role (e.g., Settings tab for admins only)?

---

# DESIGN DECISION #6: Members Invite Modal (3h) ✅ LOW RISK

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/members/page.tsx`  
**Current Status:** 🟡 Role selector verbose, mobile-unfriendly

## 1. Current UX Problem

### Verification

**Current Modal:**
```
┌────────────────────────────┐
│ Invite Team Member         │
├────────────────────────────┤
│ Email: [________]          │
│ Role:                      │
│  ○ Tester                  │
│    Paragraph description   │
│    spanning 3 lines        │
│                            │
│  ○ QA Lead                 │
│    Another paragraph       │
│    description             │
│                            │
│ Permissions: [Toggle]      │
│ [Learn more ↗]             │
│                            │
│ [Cancel] [Invite]          │
└────────────────────────────┘
```

**Problems:**
- 📱 Mobile (375px): text wraps, modal width fixed (unreadable)
- 😕 Role descriptions: verbose (users skip reading)
- ❓ Permissions tab: separate, confusing
- 🧐 Role differences: unclear (lack of icons)

---

## 2. Proposed Solution

### Redesigned Invite Modal
```
┌──────────────────────────────┐
│ Invite Team Member           │
├──────────────────────────────┤
│ Email: [____________]        │
│                              │
│ Role:                        │
│ ┌──────────────────────────┐ │
│ │ 🧪 Tester               │ │ ← Icon + name
│ │ Run tests, view results  │ │ ← Compact description
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ 👑 QA Lead              │ │
│ │ Full test access        │ │
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ ⚙️ Manager               │ │
│ │ Project admin, billing   │ │
│ └──────────────────────────┘ │
│                              │
│ [Cancel] [Invite]            │
└──────────────────────────────┘
```

---

## 3. Implementation Details

### InviteModal Component
```tsx
// _components/InviteModal.tsx
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

const ROLES = [
  {
    id: 'tester',
    label: 'Tester',
    icon: '🧪',
    description: 'Run tests, view results',
  },
  {
    id: 'qa_lead',
    label: 'QA Lead',
    icon: '👑',
    description: 'Full test access, manage team',
  },
  {
    id: 'manager',
    label: 'Manager',
    icon: '⚙️',
    description: 'Project admin, billing',
  },
  {
    id: 'admin',
    label: 'Admin',
    icon: '🔐',
    description: 'Full organization control',
  },
];

export function InviteModal({ open, onOpenChange }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [email, setEmail] = useState('');
  const [selectedRole, setSelectedRole] = useState('tester');
  const [loading, setLoading] = useState(false);

  const handleInvite = async () => {
    setLoading(true);
    try {
      await apiClient.post('/api/v1/management/members/invite', {
        email,
        role: selectedRole,
      });
      toast.success('Invitation sent');
      onOpenChange(false);
      setEmail('');
    } catch (error) {
      toast.error('Failed to send invitation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-w-[95vw]">
        <DialogHeader>
          <h2 className="text-lg font-semibold">Invite Team Member</h2>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Email Input */}
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Email Address
            </label>
            <Input
              id="email"
              type="email"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          {/* Role Selection */}
          <div className="space-y-3">
            <p className="text-sm font-medium">Role</p>
            <RadioGroup value={selectedRole} onValueChange={setSelectedRole}>
              {ROLES.map((role) => (
                <label
                  key={role.id}
                  className={cn(
                    'flex items-start space-x-3 p-4 border rounded-lg cursor-pointer',
                    'transition-colors hover:bg-gray-50 dark:hover:bg-gray-900',
                    selectedRole === role.id &&
                      'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                  )}
                >
                  <RadioGroupItem value={role.id} className="mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">
                      {role.icon} {role.label}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      {role.description}
                    </p>
                  </div>
                </label>
              ))}
            </RadioGroup>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleInvite}
            disabled={!email || loading}
            loading={loading}
          >
            Send Invitation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 4. Risk Assessment ✅ LOW RISK

### Breaking Changes
❌ **None** — Pure UX improvement, no API changes.

### Complexity
🟢 **Low** — Only UI refactoring:
- Replace text descriptions with icon + brief text
- Adjust modal padding/spacing
- Add role icons (emoji or SVG)

### Testing
| Test Type | Scenario |
|-----------|----------|
| Visual | Modal render on mobile/desktop |
| Interaction | Select role → visual feedback |
| Email validation | Invalid email → error |
| Invite submission | Valid data → success toast |

---

## 5. Approval Checkpoint ✅ NO APPROVAL NEEDED

**Approval Required:** ❌ **NO** — Low-risk cosmetic improvement

---

# DESIGN DECISION #7: Quick Actions Hierarchy (3h) ✅ LOW RISK

**File:** `apps/web/app/(dashboard)/p/[projectId]/management/dashboard/page.tsx`  
**Current Status:** 🔴 8 buttons, no hierarchy, mobile unreadable

## 1. Current UX Problem

### Verification

**Current State:**
```
┌────────────────────────────────────────────┐
│ [Run Tests] [Create Case] [+ Step]         │
│ [View Report] [Export] [Settings] [?] [⟳] │
└────────────────────────────────────────────┘

Mobile:
┌──────────────────┐
│ [Run T...] [Cr..] │ (wraps awkwardly)
│ [+ Ste..] [View..] │
│ ...                │
└──────────────────┘
```

**Problems:**
- 🎯 No CTA hierarchy (all look equal)
- 👥 User unsure which button to click
- 📱 Mobile: 8 buttons don't fit

---

## 2. Proposed Solution

### Hierarchy: Primary > Secondary > Tertiary
```
┌──────────────────────────────────────┐
│ Primary Actions (desktop/mobile):    │
│ [Run Tests] [Create Case]            │
│                                      │
│ Secondary Actions (dropdown):        │
│ [More ▼]                             │
│   ├─ Add Step                        │
│   ├─ View Report                     │
│   ├─ Export                          │
│   └─ Schedule                        │
│                                      │
│ Tertiary (compact, right side):      │
│ [⚙️] [?]                             │
└──────────────────────────────────────┘
```

---

## 3. Implementation
```tsx
<div className="flex gap-2 flex-wrap items-center justify-between">
  <div className="flex gap-2">
    <Button onClick={runTests} size="sm">
      Run Tests
    </Button>
    <Button variant="outline" onClick={createCase} size="sm">
      Create Case
    </Button>
  </div>

  <DropdownMenu>
    <Button variant="outline" size="sm">
      More ▼
    </Button>
    <DropdownMenuContent>
      <DropdownMenuItem onClick={addStep}>Add Step</DropdownMenuItem>
      <DropdownMenuItem onClick={viewReport}>View Report</DropdownMenuItem>
      <DropdownMenuItem onClick={exportData}>Export</DropdownMenuItem>
      <DropdownMenuItem onClick={schedule}>Schedule</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>

  <div className="flex gap-2">
    <Button variant="ghost" size="sm" onClick={openSettings}>
      ⚙️
    </Button>
    <Button variant="ghost" size="sm" onClick={openHelp}>
      ?
    </Button>
  </div>
</div>
```

---

## 4. Approval Checkpoint ✅ NO APPROVAL NEEDED

**Approval Required:** ❌ **NO** — Low-risk refinement

---

# SUMMARY TABLE

| # | Decision | Problem | Solution | Effort | Risk | Approval |
|---|----------|---------|----------|--------|------|----------|
| 1 | Case Responsive Sidebar | Mobile layout broken | Accordion + responsive grid | 5h | 🟠 Medium | ✅ YES |
| 2 | Step DnD + Undo | No reorder feedback | Optimistic update + undo | 7h | 🟠 Medium | ✅ YES |
| 3 | Defects Mobile Filter | Filters hidden | Dropdown + sticky header | 6h | 🟠 Medium | ✅ YES |
| 4 | Defects Card View | No mobile fallback | Card layout + redesign | **8h** | 🔴 **HIGH** | ✅ **YES — user test required** |
| 5 | Dashboard Tabs | 40+ widgets overload | Tab structure (5 tabs) | **12h** | 🔴 **HIGH** | ✅ **YES — major change** |
| 6 | Members Invite Modal | Verbose role picker | Icon + compact description | 3h | 🟢 Low | ❌ NO |
| 7 | Quick Actions | No button hierarchy | Primary/Secondary/Tertiary | 3h | 🟢 Low | ❌ NO |
| **TOTAL** | | | | **44h** | **2 High + 4 Medium + 1 Low** | **5 require approval** |

---

# IMPLEMENTATION ROADMAP

## Sprint 1 (Week 1): Low-Risk Foundation
- ✅ #6: Members Invite Modal (3h)
- ✅ #7: Quick Actions Hierarchy (3h)
- ✅ #3: Defects Mobile Filter Pattern (6h)
- **Total: 12h**

## Sprint 2 (Week 2): Medium-Risk Core Changes
- ✅ #1: Case Responsive Sidebar (5h)
- ✅ #2: Step DnD + Undo (7h)
- **Total: 12h**

## Sprint 3 (Week 3): High-Risk + Testing
- 🔴 #4: Defects Card View (8h) + *User testing*
- 🔴 #5: Dashboard Tabs (12h) + *User testing*
- **Total: 20h**

---

# APPROVAL CHECKLIST

Before proceeding, obtain written approval from:

- [ ] **Product Manager** — Validates all 7 decisions align with roadmap
- [ ] **Design Lead** — Approves wireframes, responsive breakpoints, visual hierarchy
- [ ] **UX Researcher** — Designs user testing for #4 & #5 (10+ users each)
- [ ] **Engineering Director** — Confirms feasibility, maintenance cost, rollback plans

**Timeline for Approval:** 1 week  
**Timeline for Implementation:** 3 weeks  
**Timeline for User Testing:** Parallel with implementation

---

**Document prepared by:** Claude Code  
**Date:** 2026-06-09  
**Status:** 🔴 Awaiting Approval  
**Next Steps:** Present to stakeholders, collect feedback, schedule implementation sprints
