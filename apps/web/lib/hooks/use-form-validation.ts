/**
 * useFormValidation hook - manages form field validation state
 * Related to Finding #2: Form validation schema implementation
 */
import { useState, useCallback } from "react";

export interface ValidationRule {
  required?: boolean | string;
  minLength?: { value: number; message: string };
  maxLength?: { value: number; message: string };
  pattern?: { value: RegExp; message: string };
  custom?: (value: any) => string | null;
}

export interface FieldState {
  value: any;
  error: string | null;
  touched: boolean;
  isDirty: boolean;
}

export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  rules?: Record<keyof T, ValidationRule>
) {
  const [fields, setFields] = useState<Record<keyof T, FieldState>>(() => {
    const initial: Record<keyof T, FieldState> = {} as any;
    for (const key in initialValues) {
      initial[key as keyof T] = {
        value: initialValues[key],
        error: null,
        touched: false,
        isDirty: false,
      };
    }
    return initial;
  });

  const validateField = useCallback(
    (fieldName: keyof T, value: any): string | null => {
      const rule = rules?.[fieldName];
      if (!rule) return null;

      // Required check
      if (rule.required) {
        if (!value || (typeof value === "string" && !value.trim())) {
          return typeof rule.required === "string"
            ? rule.required
            : "This field is required";
        }
      }

      if (!value) return null;

      // Min length
      if (rule.minLength && value.length < rule.minLength.value) {
        return rule.minLength.message;
      }

      // Max length
      if (rule.maxLength && value.length > rule.maxLength.value) {
        return rule.maxLength.message;
      }

      // Pattern
      if (rule.pattern && !rule.pattern.value.test(value)) {
        return rule.pattern.message;
      }

      // Custom validator
      if (rule.custom) {
        return rule.custom(value);
      }

      return null;
    },
    [rules]
  );

  const setFieldValue = useCallback(
    (fieldName: keyof T, value: any) => {
      setFields((prev) => ({
        ...prev,
        [fieldName]: {
          ...prev[fieldName],
          value,
          isDirty: true,
          error: validateField(fieldName, value),
        },
      }));
    },
    [validateField]
  );

  const setFieldTouched = useCallback((fieldName: keyof T, touched: boolean) => {
    setFields((prev) => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        touched,
      },
    }));
  }, []);

  const validateAllFields = useCallback((): boolean => {
    let isValid = true;
    setFields((prev) => {
      const updated = { ...prev };
      for (const fieldName in prev) {
        const field = prev[fieldName as keyof T];
        const error = validateField(fieldName as keyof T, field.value);
        if (error) isValid = false;
        updated[fieldName as keyof T] = {
          ...field,
          error,
          touched: true,
        };
      }
      return updated;
    });
    return isValid;
  }, [validateField]);

  const reset = useCallback(() => {
    setFields((prev) => {
      const updated = { ...prev };
      for (const key in initialValues) {
        updated[key as keyof T] = {
          value: initialValues[key as keyof T],
          error: null,
          touched: false,
          isDirty: false,
        };
      }
      return updated;
    });
  }, [initialValues]);

  const getFieldProps = useCallback(
    (fieldName: keyof T) => ({
      value: fields[fieldName].value,
      onChange: (e: any) => setFieldValue(fieldName, e.target.value),
      onBlur: () => setFieldTouched(fieldName, true),
      error:
        fields[fieldName].touched && fields[fieldName].error
          ? fields[fieldName].error
          : null,
    }),
    [fields, setFieldValue, setFieldTouched]
  );

  return {
    fields,
    setFieldValue,
    setFieldTouched,
    validateField,
    validateAllFields,
    reset,
    getFieldProps,
  };
}
