# @neurex/design-system

Neurex'in paylaşılan tasarım sistemi — token'lar, primitive'ler, pattern'ler.

## Kullanım

```ts
import {
  // Primitives
  Button, Input, Textarea, Badge,
  Card, CardHeader, CardBody, CardFooter,
  Label, FieldHelp,
  Switch, Checkbox, Radio, RadioGroup, Select,
  Skeleton, SkeletonText, SkeletonCard,
  Spinner, Progress, Divider, Alert,
  ToastProvider, useToast,
  Dialog, DropdownMenu, Popover,
  Tabs, TabPanel, Accordion, Breadcrumb, Pagination,
  FormField,
  Stepper, Toolbar, ToolbarSeparator, ToolbarGroup, FileInput,
  Avatar, AvatarGroup,
  Sparkline, Tooltip, Kbd, EmptyState,
  // Patterns
  StatCard, VirtualList, ActivityHeatmap, DataTable, CommandPalette,
  // Tokens
  surfaces, text, statusBadge, productMeta,
  density, focusRing, focusRingDanger, animate, interactive,
  // Utils
  cn,
  // Hooks
  useDebounce, useMediaQuery, breakpoints,
  useLocalStorage, useCopyToClipboard, useClickOutside, useDarkMode,
} from "@neurex/design-system";
```

CSS tokens'ı global olarak yüklemek için:
```ts
import "@neurex/design-system/tokens.css";
```

## Primitives

| Component | Notlar |
|-----------|--------|
| `Button` | 8 variant, 5 size, loading state, leading/trailing icon, fullWidth, ref forward |
| `Input` / `Textarea` | invalid state, leading/trailing icon, 3 size |
| `Badge` | 5 status, dot indicator, interactive (chip) modu |
| `Card` / `CardHeader` / `CardBody` / `CardFooter` | borderless / interactive / compact varyasyonları |
| `Label` / `FieldHelp` | required göstergesi, description, invalid alert role |
| `Switch` | `role=switch`, 2 size, label assoc, disabled |
| `Checkbox` | indeterminate, invalid, description, label |
| `Radio` / `RadioGroup` | tek + grup, controlled/uncontrolled, horizontal/vertical |
| `Select` | options/children, placeholder, 3 size, invalid |
| `Skeleton` / `SkeletonText` / `SkeletonCard` | shape (rect/circle/text), sr-only label, no-anim test modu |
| `Spinner` | 4 size + numeric, label opsiyonel (null = decorative) |
| `Progress` | determinate/indeterminate, 3 size, 4 status, aria-valuenow |
| `Divider` | horizontal/vertical, label-in-middle, subtle |
| `Alert` | 4 variant (info/success/warning/danger), title, icon, dismissable |
| `ToastProvider` + `useToast` | toast/success/error/warning/info helpers, position, max limit, action button, manual dismiss |
| `Dialog` | controlled, aria-modal + labelledby/describedby, ESC/overlay close (opt-out), body scroll lock, focus trap, restore previous focus, 5 size, footer slot |
| `DropdownMenu` | render-prop trigger, heading/separator/item/danger, keyboard nav (↑↓ Home End Enter Esc), align/side, click-outside close |
| `Tabs` + `TabPanel` | line/pills variant, 2 size, badge slot, controlled+uncontrolled, ←→ Home End keyboard nav, disabled skip |
| `Accordion` | single/multiple, collapsible, controlled+uncontrolled, disabled, aria-expanded + region linking |
| `Breadcrumb` | nav role, aria-current=page on last, custom separator, maxItems collapsing with "…", href/onClick items |
| `Pagination` | smart range with edges/ellipsis, configurable sibling count, Prev/Next, aria-current=page, hide-when-1 |
| `Popover` | render-prop trigger (controlled/uncontrolled), 4 side × 3 align, ESC + click-outside close (opt-out), modal flag, sideOffset |
| `FormField` | Label + control + description + error composer; auto useId, aria-invalid + aria-describedby wiring; works with cloneElement or render-prop |
| `Stepper` | horizontal/vertical, controlled active, click-to-jump on complete steps, error status, connector lines |
| `Toolbar` + `ToolbarGroup` + `ToolbarSeparator` | role=toolbar (horizontal/vertical), grouped buttons, label slots |
| `FileInput` | button + dropzone variants, accept (MIME or .ext), maxSize, multiple, drag-drop, onFilesRejected callback |
| `Avatar` / `AvatarGroup` | initials fallback, status dot, gradient hash, +N overflow |
| `Sparkline` | Inline trend grafiği |
| `Tooltip` | Radix tooltip wrapper |
| `Kbd` | Klavye kısayolu görseli |
| `EmptyState` | Veri yok / hata / boş liste için |

## Patterns

`CommandPalette` — Spotlight-tarzı keyboard-driven launcher:
```ts
<CommandPalette
  open={open}
  onOpenChange={setOpen}
  items={[
    { id: "n1", label: "Yeni proje", group: "Eylemler", shortcut: "⌘N",
      onSelect: createProject },
    { id: "n2", label: "Yeni senaryo", group: "Eylemler",
      keywords: ["test", "case"], onSelect: createScenario },
    // …
  ]}
/>
```
- Tokenize edilmiş query: her token label + keywords içinde aranır.
- Group başlıkları otomatik üretilir.
- ↑↓ ile gez, Enter ile seç, ESC kapat, Home/End uçlara atla.
- Mouse hover'da active item güncellenir.
- disabled item'lar keyboard nav'da atlanır.

`DataTable<TRow>` — generic, type-safe, sortable, paginated table:
```ts
<DataTable
  data={projects}
  columns={columns}
  rowKey={p => p.id}
  striped
  interactive
  loading={isLoading}
  totalRows={42}
  pagination={{ page, pageSize: 10, onPageChange: setPage }}
/>
```

Özellikler: 3-aşamalı sort cycle (asc→desc→kapalı), controlled+uncontrolled,
aria-sort, loading→N satır skeleton, otomatik EmptyState (custom slot ile
override), onRowClick, striped/dense/stickyHeader/interactive, hidden kolon,
Pagination entegrasyonu (server-side için `totalRows`).

## Hooks

```ts
// Debounced search input
const debouncedQuery = useDebounce(query, 300);

// Responsive breakpoints (Tailwind uyumlu)
const isDesktop = useMediaQuery(breakpoints.lg);

// Cross-tab persistent state
const [theme, setTheme, removeTheme] = useLocalStorage("theme", "dark");

// Clipboard with reset
const { copied, copy } = useCopyToClipboard(2000);

// Outside click → close
const ref = useClickOutside<HTMLDivElement>(() => setOpen(false));

// Theme management (system / light / dark)
const { theme, setTheme, isDark } = useDarkMode();
```

Tüm hook'lar SSR-safe — `window`/`navigator`/`document` yokken default'lara
düşer ve mount sonrası senkronize olur.

## Storybook

```bash
npm run dev -w @neurex/storybook    # http://localhost:6006
```

Her primitive için `*.stories.tsx` mevcut — bütün variant/size/state örnekleri
tek sayfada.

## Token kullanımı

Doğrudan Tailwind class'ları varsa onları tercih et:
```tsx
<div className="bg-surface-raised text-fg-muted border border-border" />
```

Dinamik (runtime) class seçimi gerektiğinde token helper'ları kullan:
```tsx
import { statusBadge, surfaces, density } from "@neurex/design-system/tokens";

<span className={statusBadge[status]}>{label}</span>
<div className={surfaces[level]}>{children}</div>
<button className={`${density.compact.padding} ${density.compact.text}`}>OK</button>
```

## Test

```bash
npm test -w @neurex/design-system        # vitest + jsdom
npm run test:watch -w @neurex/design-system
```

Unit testler (Avatar, Button, Input, Badge, Card, Label, Switch, Checkbox,
Radio, RadioGroup, Select, cn utility) — focus state, aria-invalid, ref
forwarding, controlled/uncontrolled, indeterminate, role-doğru elementler.
