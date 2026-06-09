"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Sistematik başlık ölçeği — ad-hoc `font-bold`/`text-sm`-as-heading kullanımının yerine.
 * `level` görsel ölçeği, `as` ise semantic HTML etiketini belirler (a11y için ayrılmıştır).
 */
const headingVariants = cva("font-semibold tracking-tight text-fg", {
  variants: {
    level: {
      1: "text-4xl font-bold",
      2: "text-2xl font-semibold",
      3: "text-lg font-semibold",
      4: "text-base font-semibold",
      5: "text-sm font-semibold",
      6: "text-xs font-semibold uppercase tracking-wider text-fg-subtle",
    },
  },
  defaultVariants: { level: 2 },
});

type HeadingTag = "h1" | "h2" | "h3" | "h4" | "h5" | "h6";

export interface HeadingProps
  extends React.HTMLAttributes<HTMLHeadingElement>,
    VariantProps<typeof headingVariants> {
  /** Görsel ölçekten bağımsız semantic etiket (a11y outline'ı korumak için). */
  as?: HeadingTag;
}

export function Heading({ className, level, as, children, ...props }: HeadingProps) {
  const Tag = (as ?? `h${level ?? 2}`) as HeadingTag;
  return (
    <Tag className={cn(headingVariants({ level }), className)} {...props}>
      {children}
    </Tag>
  );
}
