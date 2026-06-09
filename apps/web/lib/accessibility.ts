/**
 * Accessibility Utilities — WCAG 2.1 AAA Compliance
 *
 * - Color contrast validation
 * - Focus management
 * - Keyboard navigation
 * - ARIA helpers
 * - Screen reader announcements
 */

// ────────────────────────────────────────────────────────────
// Color Contrast Analysis (WCAG AA/AAA)
// ────────────────────────────────────────────────────────────

/**
 * Calculate relative luminance (WCAG formula)
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Parse color string to RGB
 */
function parseColor(color: string): [number, number, number] | null {
  // Handle hex colors
  const hexMatch = color.match(/^#([0-9a-f]{6})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    return [
      parseInt(hex.substr(0, 2), 16),
      parseInt(hex.substr(2, 2), 16),
      parseInt(hex.substr(4, 2), 16),
    ];
  }

  // Handle rgb()
  const rgbMatch = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (rgbMatch) {
    return [parseInt(rgbMatch[1]), parseInt(rgbMatch[2]), parseInt(rgbMatch[3])];
  }

  return null;
}

/**
 * Calculate contrast ratio (WCAG)
 */
export function getContrastRatio(foreground: string, background: string): number {
  const fgRgb = parseColor(foreground);
  const bgRgb = parseColor(background);

  if (!fgRgb || !bgRgb) {
    return 0;
  }

  const fgLum = getLuminance(...fgRgb);
  const bgLum = getLuminance(...bgRgb);

  const lighter = Math.max(fgLum, bgLum);
  const darker = Math.min(fgLum, bgLum);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Validate contrast ratio
 */
export function validateContrast(
  foreground: string,
  background: string,
  level: "AA" | "AAA" = "AA"
): { pass: boolean; ratio: number; required: number } {
  const ratio = getContrastRatio(foreground, background);
  const required = level === "AAA" ? 7 : 4.5;

  return {
    pass: ratio >= required,
    ratio: Math.round(ratio * 100) / 100,
    required,
  };
}

// ────────────────────────────────────────────────────────────
// Focus Management
// ────────────────────────────────────────────────────────────

/**
 * Focus an element, handling all cases
 */
export function focusElement(el: HTMLElement | null): void {
  if (!el) return;

  // If already focused, blur first to ensure focus event fires
  if (document.activeElement === el) {
    (el as HTMLElement).blur();
  }

  el.focus({ preventScroll: false });
}

/**
 * Get focus visible state
 */
export function isFocusVisible(el: Element): boolean {
  return (
    el.matches(":focus-visible") ||
    (el as any).matches(":-webkit-focus-visible") ||
    el.matches(":focus")
  );
}

/**
 * Manage focus trap (for modals, menus)
 */
export interface FocusTrapOptions {
  initialFocus?: HTMLElement;
  restoreFocus?: boolean;
  onEscape?: () => void;
}

export class FocusTrap {
  private element: HTMLElement;
  private previousActiveElement: Element | null;
  private options: FocusTrapOptions;
  private focusableElements: HTMLElement[] = [];
  private handleKeyDown = (e: KeyboardEvent) => this._handleKeyDown(e);

  constructor(element: HTMLElement, options: FocusTrapOptions = {}) {
    this.element = element;
    this.previousActiveElement = null;
    this.options = options;
  }

  activate(): void {
    this.previousActiveElement = document.activeElement;

    // Find all focusable elements
    const selector = [
      "a[href]",
      "button:not([disabled])",
      "textarea:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "[tabindex]:not([tabindex=\"-1\"])",
    ].join(", ");

    this.focusableElements = Array.from(this.element.querySelectorAll(selector));

    // Set initial focus
    const initialFocus = this.options.initialFocus || this.focusableElements[0];
    if (initialFocus) {
      focusElement(initialFocus as HTMLElement);
    }

    // Listen for keyboard events
    document.addEventListener("keydown", this.handleKeyDown);
  }

  deactivate(): void {
    document.removeEventListener("keydown", this.handleKeyDown);

    // Restore previous focus
    if (this.options.restoreFocus && this.previousActiveElement) {
      focusElement(this.previousActiveElement as HTMLElement);
    }
  }

  private _handleKeyDown(e: KeyboardEvent): void {
    if (e.key === "Escape") {
      e.preventDefault();
      this.options.onEscape?.();
      return;
    }

    if (e.key !== "Tab") return;

    const first = this.focusableElements[0];
    const last = this.focusableElements[this.focusableElements.length - 1];

    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === first) {
        e.preventDefault();
        focusElement(last);
      }
    } else {
      // Tab
      if (document.activeElement === last) {
        e.preventDefault();
        focusElement(first);
      }
    }
  }
}

// ────────────────────────────────────────────────────────────
// Keyboard Navigation
// ────────────────────────────────────────────────────────────

/**
 * Check if element is focusable
 */
export function isFocusable(element: Element): boolean {
  const selector = [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "[tabindex]",
  ].join(", ");

  return element.matches(selector);
}

/**
 * Get all focusable elements in a container
 */
export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const selector = [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "[tabindex]:not([tabindex=\"-1\"])",
  ].join(", ");

  return Array.from(container.querySelectorAll(selector));
}

/**
 * Skip to main content link helper
 */
export function createSkipLink(targetId: string): HTMLAnchorElement {
  const link = document.createElement("a");
  link.href = `#${targetId}`;
  link.textContent = "Skip to main content";
  link.className = [
    "sr-only", // Screen reader only
    "focus:not-sr-only", // Visible on focus
    "absolute", // Position absolutely
    "left-0", // Off-screen initially
    "focus:left-0", // Reset on focus
    "top-0", // Off-screen initially
    "focus:top-0", // Reset on focus
    "z-50", // High z-index
  ].join(" ");

  return link;
}

// ────────────────────────────────────────────────────────────
// ARIA Helpers
// ────────────────────────────────────────────────────────────

/**
 * Create unique ID for ARIA attributes
 */
export function createAriaId(prefix: string = "aria"): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Set ARIA live region announcement
 */
export function announceToScreenReader(
  message: string,
  priority: "polite" | "assertive" = "polite"
): void {
  let announcer = document.getElementById("aria-announcer");

  if (!announcer) {
    announcer = document.createElement("div");
    announcer.id = "aria-announcer";
    announcer.setAttribute("aria-live", priority);
    announcer.setAttribute("aria-atomic", "true");
    announcer.className = "sr-only";
    document.body.appendChild(announcer);
  }

  announcer.setAttribute("aria-live", priority);
  announcer.textContent = message;
}

/**
 * Create accessible button from div
 */
export function makeAccessibleButton(
  element: HTMLElement,
  onActivate: () => void
): void {
  element.setAttribute("role", "button");
  element.setAttribute("tabindex", "0");

  element.addEventListener("click", onActivate);
  element.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onActivate();
    }
  });
}

// ────────────────────────────────────────────────────────────
// Accessibility Audit
// ────────────────────────────────────────────────────────────

export interface AccessibilityIssue {
  type: string;
  element: Element;
  message: string;
  severity: "error" | "warning" | "info";
}

/**
 * Audit page accessibility (basic checks)
 */
export function auditAccessibility(): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];

  // Check for missing alt text on images
  document.querySelectorAll("img").forEach((img) => {
    if (!img.hasAttribute("alt")) {
      issues.push({
        type: "missing-alt",
        element: img,
        message: "Image missing alt text",
        severity: "error",
      });
    }
  });

  // Check for form fields without labels
  document.querySelectorAll("input, textarea, select").forEach((field) => {
    const id = field.id;
    if (id && !document.querySelector(`label[for="${id}"]`)) {
      issues.push({
        type: "missing-label",
        element: field,
        message: "Form field missing associated label",
        severity: "warning",
      });
    }
  });

  // Check for color contrast
  document.querySelectorAll("a, button, p, span").forEach((el) => {
    const style = window.getComputedStyle(el);
    const color = style.color;
    const bgColor = style.backgroundColor;

    const ratio = getContrastRatio(color, bgColor);
    if (ratio < 4.5) {
      issues.push({
        type: "low-contrast",
        element: el,
        message: `Low contrast ratio: ${ratio.toFixed(2)}:1 (required: 4.5:1)`,
        severity: "warning",
      });
    }
  });

  // Check for headings in order
  const headings = Array.from(document.querySelectorAll("h1, h2, h3, h4, h5, h6"));
  let prevLevel = 0;
  headings.forEach((heading) => {
    const level = parseInt(heading.tagName[1]);
    if (level - prevLevel > 1) {
      issues.push({
        type: "heading-order",
        element: heading,
        message: `Heading level skipped from h${prevLevel} to h${level}`,
        severity: "warning",
      });
    }
    prevLevel = level;
  });

  // Check for page title
  if (!document.title) {
    issues.push({
      type: "missing-title",
      element: document.head,
      message: "Page title is missing",
      severity: "error",
    });
  }

  return issues;
}

// ────────────────────────────────────────────────────────────
// Screen Reader Only Content
// ────────────────────────────────────────────────────────────

/**
 * CSS classes for screen reader only content
 */
export const srOnlyStyles = `
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }

  .focus\\:not-sr-only:focus {
    position: static;
    width: auto;
    height: auto;
    padding: inherit;
    margin: inherit;
    overflow: visible;
    clip: auto;
    white-space: normal;
  }
`;

/**
 * Create screen reader only element
 */
export function createScreenReaderOnly(text: string): HTMLElement {
  const element = document.createElement("span");
  element.className = "sr-only";
  element.textContent = text;
  return element;
}

// ────────────────────────────────────────────────────────────
// Reduced Motion Support
// ────────────────────────────────────────────────────────────

/**
 * Check if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;

  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Listen for reduced motion preference changes
 */
export function onReducedMotionChange(callback: (prefersReduced: boolean) => void): () => void {
  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  const handleChange = (e: MediaQueryListEvent) => {
    callback(e.matches);
  };

  mediaQuery.addEventListener("change", handleChange);

  // Call immediately with current value
  callback(mediaQuery.matches);

  return () => mediaQuery.removeEventListener("change", handleChange);
}

// ────────────────────────────────────────────────────────────
// High Contrast Mode Support
// ────────────────────────────────────────────────────────────

/**
 * Check if user prefers high contrast
 */
export function prefersHighContrast(): boolean {
  if (typeof window === "undefined") return false;

  return window.matchMedia("(prefers-contrast: more)").matches;
}

/**
 * Check if user uses dark mode
 */
export function prefersDarkMode(): boolean {
  if (typeof window === "undefined") return false;

  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
