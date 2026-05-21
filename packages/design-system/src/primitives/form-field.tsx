"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { Label } from "./label";
import { FieldHelp } from "./label";

export interface FormFieldProps {
  /** Etiket */
  label?: React.ReactNode;
  /** Yardımcı metin (her zaman görünür) */
  description?: React.ReactNode;
  /** Hata metni — varsa invalid olarak işaretlenir */
  error?: React.ReactNode;
  /** Required göstergesi */
  required?: boolean;
  /** Child control'a verilecek id (boşsa otomatik) */
  htmlFor?: string;
  /** Child render — input/textarea/select gibi */
  children: React.ReactNode | ((api: {
    id: string;
    "aria-invalid": boolean | undefined;
    "aria-describedby": string | undefined;
  }) => React.ReactNode);
  className?: string;
  /** Label gizli, sadece a11y için (visually hidden) */
  labelHidden?: boolean;
}

/**
 * FormField — Label + control + FieldHelp/error'ı tek noktada birleştirir.
 *
 * Otomatik:
 * - htmlFor + id eşleme (useId)
 * - aria-invalid (error varsa)
 * - aria-describedby (description + error)
 * - error varsa kırmızı help metni (role=alert)
 *
 * İki kullanım:
 *   <FormField label="E-posta" required>
 *     <Input type="email" />
 *   </FormField>
 *
 *   <FormField label="E-posta" error="Geçersiz">
 *     {api => <Input type="email" {...api} />}
 *   </FormField>
 */
export function FormField({
  label,
  description,
  error,
  required,
  htmlFor,
  children,
  className,
  labelHidden,
}: FormFieldProps) {
  const reactId = React.useId();
  const id = htmlFor ?? reactId;
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const isInvalid = Boolean(error);
  const describedBy = [
    description ? helpId : null,
    error ? errorId : null,
  ].filter(Boolean).join(" ") || undefined;

  const childApi = {
    id,
    "aria-invalid": isInvalid || undefined,
    "aria-describedby": describedBy,
  } as const;

  const child = typeof children === "function"
    ? children(childApi)
    : React.isValidElement(children)
      ? React.cloneElement(children as React.ReactElement<Record<string, unknown>>, childApi)
      : children;

  return (
    <div className={cn("w-full", className)}>
      {label && (
        <Label
          htmlFor={id}
          required={required}
          className={cn("mb-1", labelHidden && "sr-only")}
        >
          {label}
        </Label>
      )}
      {child}
      {description && !error && (
        <FieldHelp id={helpId}>{description}</FieldHelp>
      )}
      {error && (
        <FieldHelp id={errorId} invalid>
          {error}
        </FieldHelp>
      )}
    </div>
  );
}
