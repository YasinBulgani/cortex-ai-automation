"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";
import type { ProductFamilyId } from "@/lib/product";
import type { ProductTelemetry } from "./telemetry-types";
import { DEMO_TELEMETRY } from "./demo-data";

const POLL_INTERVAL = 60_000;

export function useProductTelemetry(productId: ProductFamilyId): {
  telemetry: ProductTelemetry | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
  isDemo: boolean;
  /** Sayfa global demo değil ama bazı stat'lar demo/şablon (real:false) — karışık provenance. */
  partialDemo: boolean;
} {
  const [telemetry, setTelemetry] = useState<ProductTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const isMounted = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      const data = await apiFetch<ProductTelemetry>(`/api/v1/products/${productId}/telemetry`);
      if (!isMounted.current) return;
      const dataModeIsDemo = Boolean(
        data.isDemo ||
        (data as ProductTelemetry & { demo_mode?: boolean; _demo?: unknown }).demo_mode ||
        (data as ProductTelemetry & { _demo?: unknown })._demo,
      );
      setTelemetry({ ...data, isDemo: dataModeIsDemo });
      setIsDemo(dataModeIsDemo);
      setError(null);
    } catch (err) {
      if (!isMounted.current) return;
      const demo = DEMO_TELEMETRY[productId];
      setTelemetry(demo ?? null);
      setIsDemo(true);
      setError(err instanceof Error ? err : new Error("Ürün telemetri endpoint'i yanıt vermedi"));
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    isMounted.current = true;
    setLoading(true);
    fetchData();
    const timer = setInterval(fetchData, POLL_INTERVAL);
    return () => {
      isMounted.current = false;
      clearInterval(timer);
    };
  }, [fetchData]);

  // Karışık provenance: global demo değil ama en az bir stat real:false.
  const partialDemo =
    !isDemo && Boolean(telemetry?.stats?.some((s) => s.real === false));

  return { telemetry, loading, error, refresh: fetchData, isDemo, partialDemo };
}
