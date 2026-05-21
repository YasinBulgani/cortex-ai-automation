"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useCopyToClipboard — bir string'i clipboard'a kopyalar ve geçici durum döner.
 *
 * @example
 *   const { copied, copy, error } = useCopyToClipboard();
 *   <button onClick={() => copy("hello")}>{copied ? "✓" : "Kopyala"}</button>
 */
export function useCopyToClipboard(reset_ms = 2000): {
  copied: boolean;
  copy: (text: string) => Promise<boolean>;
  error: Error | null;
} {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      setError(null);
      if (typeof navigator === "undefined" || !navigator.clipboard) {
        const err = new Error("Clipboard API not available");
        setError(err);
        return false;
      }
      try {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setCopied(false), reset_ms);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
        return false;
      }
    },
    [reset_ms],
  );

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return { copied, copy, error };
}
