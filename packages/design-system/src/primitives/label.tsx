"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
  description?: React.ReactNode;
  size?: "sm" | "md";
}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(function Label(
  { required, description, size = "sm", className, children, ...rest },
  ref,
) {
  return (
    <label
      ref={ref}
      className={cn(
        "block font-medium text-fg",
        size === "sm" ? "text-xs" : "text-sm",
        rest.htmlFor && "cursor-pointer",
        className,
      )}
      {...rest}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {required && (
          <span className="text-danger" aria-label="required">*</span>
        )}
      </span>
      {description && (
        <span className="mt-0.5 block font-normal text-fg-subtle">{description}</span>
      )}
    </label>
  );
});

export interface FieldHelpProps extends React.HTMLAttributes<HTMLParagraphElement> {
  invalid?: boolean;
}

export function FieldHelp({ invalid, className, ...rest }: FieldHelpProps) {
  return (
    <p
      className={cn(
        "mt-1 text-xs",
        invalid ? "text-danger" : "text-fg-subtle",
        className,
      )}
      role={invalid ? "alert" : undefined}
      {...rest}
    />
  );
}
