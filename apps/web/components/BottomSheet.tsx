/**
 * BottomSheet — Mobile-first modal alternative
 * Slides up from bottom, optional swipe-to-dismiss, responsive
 */

import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
  snapPoints?: ("full" | number)[]; // "full" = 100%, number = px from bottom
  initialSnap?: 0 | 1 | 2;
  dismissible?: boolean;
}

export function BottomSheet({
  isOpen,
  onClose,
  title,
  children,
  className = "",
  snapPoints = ["full"],
  initialSnap = 0,
  dismissible = true,
}: BottomSheetProps) {
  const [snapIndex, setSnapIndex] = useState(initialSnap);
  const [isDragging, setIsDragging] = useState(false);
  const [startY, setStartY] = useState(0);
  const [currentTranslate, setCurrentTranslate] = useState(0);
  const sheetRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Get height for snap point
  const getSnapHeight = (point: string | number, containerHeight: number): number => {
    if (point === "full") return containerHeight;
    return Math.min(point as number, containerHeight);
  };

  // Handle touch start
  const handleTouchStart = (e: React.TouchEvent) => {
    if (!dismissible) return;
    setIsDragging(true);
    setStartY(e.touches[0].clientY);
  };

  // Handle touch move
  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging || !dismissible) return;

    const diff = e.touches[0].clientY - startY;
    if (diff > 0) {
      // Only allow dragging downward
      setCurrentTranslate(diff);
    }
  };

  // Handle touch end
  const handleTouchEnd = () => {
    if (!isDragging) return;
    setIsDragging(false);

    // Close if dragged more than 20% of sheet height
    const threshold = (contentRef.current?.offsetHeight || 0) * 0.2;
    if (currentTranslate > threshold) {
      onClose();
    }

    setCurrentTranslate(0);
  };

  // Close on background click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (dismissible && e.target === e.currentTarget) {
      onClose();
    }
  };

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, dismissible, onClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-black/50 backdrop-blur-sm transition-opacity duration-300"
      onClick={handleBackdropClick}
      data-testid="bottom-sheet-overlay"
    >
      <div
        ref={sheetRef}
        className={`w-full max-h-[90vh] rounded-t-2xl bg-white dark:bg-slate-950 shadow-2xl transition-transform duration-300 ${
          isDragging ? "transition-none" : ""
        } ${className}`}
        style={{
          transform: `translateY(${currentTranslate}px)`,
          touchAction: "none",
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        data-testid="bottom-sheet"
      >
        {/* Handle / Drag indicator */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="h-1 w-12 rounded-full bg-slate-300 dark:bg-slate-700" />
        </div>

        {/* Header */}
        {title && (
          <div className="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {title}
            </h2>
          </div>
        )}

        {/* Content */}
        <div
          ref={contentRef}
          className="overflow-y-auto px-6 py-4 max-h-[calc(90vh-80px)]"
        >
          {children}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// MobileBottomNavigation — Tab bar for mobile navigation
// ────────────────────────────────────────────────────────────

export interface NavItem {
  id: string;
  label: string;
  icon: ReactNode;
  href?: string;
  onClick?: () => void;
}

export interface MobileBottomNavigationProps {
  items: NavItem[];
  activeId?: string;
  onSelect?: (id: string) => void;
  className?: string;
}

export function MobileBottomNavigation({
  items,
  activeId,
  onSelect,
  className = "",
}: MobileBottomNavigationProps) {
  return (
    <nav
      className={`fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 safe-area-inset-bottom ${className}`}
      data-testid="mobile-bottom-nav"
    >
      <div className="flex justify-around max-w-4xl mx-auto">
        {items.map((item) => (
          <a
            key={item.id}
            href={item.href || "#"}
            onClick={(e) => {
              e.preventDefault();
              onSelect?.(item.id);
              item.onClick?.();
            }}
            className={`flex flex-col items-center justify-center px-4 py-3 text-xs font-medium transition-colors ${
              activeId === item.id
                ? "text-indigo-600 dark:text-indigo-400"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
            data-testid={`nav-item-${item.id}`}
          >
            <div className="h-6 w-6 mb-1">{item.icon}</div>
            <span className="line-clamp-1">{item.label}</span>
          </a>
        ))}
      </div>
    </nav>
  );
}

// ────────────────────────────────────────────────────────────
// Touch-friendly Button wrapper
// ────────────────────────────────────────────────────────────

export interface TouchButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  haptic?: "tap" | "success" | "warning" | "error";
}

export function TouchButton({
  children,
  haptic,
  className = "",
  onClick,
  ...props
}: TouchButtonProps) {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    // Trigger haptic feedback if supported
    if (haptic && typeof navigator !== "undefined" && "vibrate" in navigator) {
      const patterns: Record<string, number | number[]> = {
        tap: 20,
        success: [20, 10, 20],
        warning: [50, 20, 50],
        error: [100, 50, 100],
      };

      try {
        (navigator as any).vibrate(patterns[haptic]);
      } catch (err) {
        // Silently ignore vibration errors
      }
    }

    onClick?.(e);
  };

  return (
    <button
      {...props}
      onClick={handleClick}
      className={`min-h-[44px] min-w-[44px] transition-transform active:scale-95 ${className}`}
      data-testid="touch-button"
    >
      {children}
    </button>
  );
}

// ────────────────────────────────────────────────────────────
// Swipeable Container
// ────────────────────────────────────────────────────────────

export interface SwipeableProps {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  threshold?: number;
  children: ReactNode;
  className?: string;
}

export function Swipeable({
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onSwipeDown,
  threshold = 50,
  children,
  className = "",
}: SwipeableProps) {
  const [startX, setStartX] = useState(0);
  const [startY, setStartY] = useState(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    setStartX(e.touches[0].clientX);
    setStartY(e.touches[0].clientY);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const endX = e.changedTouches[0].clientX;
    const endY = e.changedTouches[0].clientY;

    const diffX = startX - endX;
    const diffY = startY - endY;

    if (Math.abs(diffX) > Math.abs(diffY)) {
      // Horizontal swipe
      if (diffX > threshold) {
        onSwipeLeft?.();
      } else if (diffX < -threshold) {
        onSwipeRight?.();
      }
    } else {
      // Vertical swipe
      if (diffY > threshold) {
        onSwipeUp?.();
      } else if (diffY < -threshold) {
        onSwipeDown?.();
      }
    }
  };

  return (
    <div
      className={className}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      data-testid="swipeable"
    >
      {children}
    </div>
  );
}
