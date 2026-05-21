# Design — GAP-001

> **Input:** proposal.md (onaylı seçenek: B)  
> **By:** designer on 2023-11-15  
> **Paralel:** arch-ADR.md (architect aynı anda çalışıyor/çalıştı)

---

## User Flow

```
1. Kullanıcı ana sayfada bulunur.
2. Klavye ile sidebar'a erişir.
3. Menü öğelerini klavyeyle gezinir ve bir öğeye tıklar.
4. Seçilen menü öğesi aktif hale gelir ve kullanıcı o bölümü görür.
```

---

## Component Inventory

### Var olan bileşenler (kullanılacak)

| Bileşen | Yol | Değişiklik var mı? |
|---|---|---|
| `Button` | `apps/web/components/ui/button.tsx` | Hayır |
| `Modal` | `apps/web/components/ui/modal.tsx` | `size` prop eklenecek |

### Yeni bileşenler

| Bileşen | Yol (önerilen) | Amaç |
|---|---|---|
| `NavigationMenu` | `apps/web/components/ui/navigation-menu.tsx` | A11y-first sidebar menü |

---

## States Matrix

| Bileşen | Default | Hover | Focus | Active | Disabled | Loading | Error |
|---|---|---|---|---|---|---|---|
| `NavigationMenu.Item` | neutral bg | bg-hover | ring-2 | bg-active + indicator | opacity-50 | skeleton | border-red |

---

## Interaction Spec

| Etkileşim | Olay | Davranış |
|---|---|---|
| Tab | keydown | Bir sonraki fokuslanabilir öğeye geç |
| Enter/Space | keydown | Öğeyi aktive et |
| Esc | keydown | Menüyü kapat |
| Arrow Up/Down | keydown | Menü içinde gezin |

Animation: `transition-colors duration-150`. Reduced-motion: `motion-reduce:transition-none`.

---

## A11y Checklist

- [x] ARIA roles uygulandı (`role="navigation"`, `role="menu"`, vs.)
- [x] aria-label / aria-labelledby
- [x] aria-current="page" aktif öğede
- [x] Keyboard navigation: Tab, Enter, Esc, Arrow
- [x] Focus-visible ring
- [x] Skip-to-content link
- [x] Color contrast ≥ 4.5:1 text, ≥ 3:1 non-text
- [x] Screen reader: tüm öğeler meaningful label'lı
- [x] `prefers-reduced-motion` respect

---

## Responsive Plan

| Breakpoint | Davranış |
|---|---|
| Mobile (< 768px) | Drawer: off-canvas sol'dan kayar |
| Tablet (768-1024) | Collapsed sidebar (sadece icon) |
| Desktop (> 1024) | Full sidebar |

---

## i18n Notları

String'ler:
- `nav.dashboard` — "Dashboard"
- `nav.settings` — "Ayarlar"

TR/EN her ikisi de `apps/web/messages/`'e eklenecek.

Uzun metin taşması: `truncate` + tooltip.

---

## Edge Cases

1. **Boş state:** Menü öğesi yoksa "Henüz menü öğesi yok" placeholder
2. **Loading:** Skeleton bileşeni
3. **Error:** Retry butonlu inline error
4. **Deep nested:** 3+ seviye — flat'e düşür veya accordion

---

## Mockup

```
┌─────────────────────────────────────┐
│ [Logo] ──────────── [User Menu ▼]   │
├───────┬─────────────────────────────┤
│       │                             │
│ ◉ Dash│   Content                   │
│ ○ Set │                             │
│ ○ Help│                             │
│       │                             │
└───────┴─────────────────────────────┘
```

---

## Referanslar

- Design system: `apps/web/lib/design-tokens/`
- A11y ref: [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)
- Radix primitives: (kullanılacaksa)

---

[pipeline: designer GAP-001]
