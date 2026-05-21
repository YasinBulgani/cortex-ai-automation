"use client";

import { cn } from "@/lib/utils";

type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";
type AvatarShape = "circle" | "rounded" | "square";

const SIZE_CLASSES: Record<AvatarSize, string> = {
  xs: "h-5 w-5 text-[9px]",
  sm: "h-6 w-6 text-[10px]",
  md: "h-8 w-8 text-xs",
  lg: "h-10 w-10 text-sm",
  xl: "h-14 w-14 text-base",
};

const SHAPE_CLASSES: Record<AvatarShape, string> = {
  circle:  "rounded-full",
  rounded: "rounded-lg",
  square:  "rounded-sm",
};

const GRADIENTS = [
  "from-blue-600 to-violet-600",
  "from-emerald-600 to-teal-600",
  "from-rose-600 to-pink-600",
  "from-amber-600 to-orange-600",
  "from-cyan-600 to-sky-600",
  "from-indigo-600 to-purple-600",
  "from-fuchsia-600 to-pink-600",
  "from-green-600 to-emerald-600",
];

function hashColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return GRADIENTS[hash % GRADIENTS.length];
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map(w => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  src?: string | null;
  size?: AvatarSize;
  shape?: AvatarShape;
  seed?: string;        // Stable gradient seed (default: name)
  status?: "online" | "away" | "offline" | "busy";
  ring?: boolean;
}

export function Avatar({
  name,
  src,
  size = "md",
  shape = "rounded",
  seed,
  status,
  ring,
  className,
  ...rest
}: AvatarProps) {
  const initials = getInitials(name) || "?";
  const grad = hashColor(seed || name);

  const statusDot = status && (
    <span
      className={cn(
        "absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface-base",
        status === "online" && "bg-success",
        status === "away"   && "bg-warning",
        status === "busy"   && "bg-danger",
        status === "offline"&& "bg-fg-disabled",
      )}
      aria-label={status}
    />
  );

  return (
    <div
      className={cn(
        "relative shrink-0 inline-flex items-center justify-center font-semibold text-white",
        "bg-gradient-to-br",
        grad,
        SIZE_CLASSES[size],
        SHAPE_CLASSES[shape],
        ring && "ring-2 ring-brand-primary ring-offset-2 ring-offset-surface-base",
        className,
      )}
      {...rest}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={name} className={cn("h-full w-full object-cover", SHAPE_CLASSES[shape])} />
      ) : (
        <span>{initials}</span>
      )}
      {statusDot}
    </div>
  );
}

export interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  max?: number;
  size?: AvatarSize;
  shape?: AvatarShape;
  children: React.ReactNode;
}

export function AvatarGroup({ max = 3, size = "sm", shape = "circle", className, children, ...rest }: AvatarGroupProps) {
  const kids = Array.isArray(children) ? children : [children];
  const visible = kids.slice(0, max);
  const overflow = kids.length - max;

  return (
    <div className={cn("flex items-center -space-x-1.5", className)} {...rest}>
      {visible.map((child, i) => (
        <div key={i} className="rounded-full ring-2 ring-surface-base">
          {child}
        </div>
      ))}
      {overflow > 0 && (
        <div
          className={cn(
            "relative shrink-0 inline-flex items-center justify-center font-semibold ring-2 ring-surface-base bg-surface-overlay text-fg-muted",
            SIZE_CLASSES[size],
            SHAPE_CLASSES[shape],
          )}
        >
          +{overflow}
        </div>
      )}
    </div>
  );
}
