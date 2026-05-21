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
      setTelemetry({ ...data, isDemo: false });
      setIsDemo(false);
      setError(null);
    } catch {
      if (!isMounted.current) return;
      const demo = DEMO_TELEMETRY[productId];
      setTelemetry(demo ?? null);
      setIsDemo(true);
      setError(null);
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

  return { telemetry, loading, error, refresh: fetchData, isDemo };
}
