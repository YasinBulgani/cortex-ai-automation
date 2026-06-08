"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { startWebVitalsBeacon } from "@/lib/web-vitals-beacon";

/**
 * Core Web Vitals RUM raporlayıcısı — görünmez (null render eder).
 *
 * Her route değişiminde yeni bir ölçüm oturumu başlatır; önceki oturumun
 * gözlemcileri cleanup ile kapanır. Yalnızca kimlik doğrulamalı alanda
 * (dashboard layout) mount edilir, böylece public sayfalarda 401 üretmez.
 */
export function WebVitalsReporter() {
  const pathname = usePathname();
  useEffect(() => {
    const stop = startWebVitalsBeacon();
    return stop;
  }, [pathname]);
  return null;
}
