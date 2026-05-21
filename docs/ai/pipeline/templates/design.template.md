# Design — {{ID}}

> **Input:** proposal.md (onaylı seçenek: {A/B/C})  
> **By:** designer-{{agent_id}} on {{date}}  
> **Paralel:** arch-ADR.md (architect aynı anda çalışıyor/çalıştı)

---

## User Flow

```
1. Kullanıcı X sayfasındadır
2. Y bileşenini görür
3. Z aksiyonu alır → ...
4. Sonuç: ...
```

(Gerekirse diagram / screenshot)

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

- [ ] ARIA roles uygulandı (`role="navigation"`, `role="menu"`, vs.)
- [ ] aria-label / aria-labelledby
- [ ] aria-current="page" aktif öğede
- [ ] Keyboard navigation: Tab, Enter, Esc, Arrow
- [ ] Focus-visible ring
- [ ] Skip-to-content link
- [ ] Color contrast ≥ 4.5:1 text, ≥ 3:1 non-text
- [ ] Screen reader: tüm öğeler meaningful label'lı
- [ ] `prefers-reduced-motion` respect

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

(Veya Figma linki / SVG)

---

## Referanslar

- Design system: `apps/web/lib/design-tokens/`
- A11y ref: [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)
- Radix primitives: (kullanılacaksa)

---

[pipeline: designer {{ID}}]
