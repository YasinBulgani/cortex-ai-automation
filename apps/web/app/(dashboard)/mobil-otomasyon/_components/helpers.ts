"use client";

import React from "react";
import type { AppiumAction, BackendDevice, Device, DeviceStatus, Platform, DeviceKind } from "./types";

// ── Numeric helpers ──────────────────────────────────────────────────────────

export const rnd = (min: number, max: number) => Math.random() * (max - min) + min;
export const rndInt = (min: number, max: number) => Math.floor(rnd(min, max));
export const fmtMs = (ms: number) => (ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`);

// ── LLM step mock ────────────────────────────────────────────────────────────
/**
 * Client-side mock: converts a natural-language prompt into Appium action steps.
 * Replace with a real LLM call when backend endpoint is available.
 */
export function mockLLMStepper(prompt: string, platform: Platform): AppiumAction[] {
  const steps: AppiumAction[] = [{ action: "launch" }];
  const lower = prompt.toLowerCase();

  if (lower.includes("giriş yap") || lower.includes("login")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "login_button", timeout: 5000 },
      { action: "tap" },
    );
  }
  if (lower.includes("email")) {
    const m = prompt.match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
    steps.push(
      { action: "find", by: "accessibilityId", value: "email_input" },
      { action: "sendKeys", text: m?.[0] ?? "test@example.com" },
    );
  }
  if (lower.includes("şifre") || lower.includes("password")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "password_input" },
      { action: "sendKeys", text: "Test123!" },
    );
  }
  if (lower.includes("devam") || lower.includes("gönder") || lower.includes("submit")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "submit_button" },
      { action: "tap" },
    );
  }
  if (lower.includes("onboarding") || lower.includes("dil")) {
    steps.push(
      { action: "find", by: platform === "ios" ? "predicate" : "accessibilityId", value: "onboarding_skip" },
      { action: "tap" },
      { action: "wait", ms: 500 },
      { action: "find", by: "accessibilityId", value: "lang_tr" },
      { action: "tap" },
    );
  }
  if (lower.includes("ara") || lower.includes("arama") || lower.includes("search")) {
    const q = prompt.match(/'([^']+)'/)?.[1] ?? "kahve";
    steps.push(
      { action: "find", by: "accessibilityId", value: "search_input" },
      { action: "sendKeys", text: q },
    );
  }
  if (lower.includes("sepet")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "add_to_cart" },
      { action: "tap" },
      { action: "verifyVisible", by: "accessibilityId", value: "cart_badge_1", timeout: 3000 },
    );
  }
  if (lower.includes("çıkış")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "profile_tab" },
      { action: "tap" },
      { action: "find", by: "accessibilityId", value: "logout_button" },
      { action: "tap" },
      { action: "find", by: "accessibilityId", value: "confirm_yes" },
      { action: "tap" },
      { action: "verifyVisible", by: "accessibilityId", value: "login_screen", timeout: 5000 },
    );
  }
  if (lower.includes("ana sayfa") || lower.includes("doğrula")) {
    steps.push({
      action: "verifyVisible",
      by: "accessibilityId",
      value: "home_screen",
      timeout: 8000,
    });
  }
  if (steps.length === 1) {
    steps.push(
      { action: "wait", ms: 1000 },
      { action: "verifyVisible", by: "accessibilityId", value: "app_root", timeout: 5000 },
    );
  }
  return steps;
}

// ── Backend → UI adapter ─────────────────────────────────────────────────────

export function fromBackendDevice(d: BackendDevice): Device {
  const portMatch = d.appium_url?.match(/:(\d+)/);
  return {
    id: d.id,
    name: d.name,
    platform: d.platform,
    osVersion: d.os_version,
    profile: d.profile,
    kind: d.kind,
    status: d.status,
    battery: d.battery,
    cpuPct: d.cpu_pct,
    ramPct: d.ram_pct,
    appiumPort: portMatch ? Number(portMatch[1]) : 4723,
    currentStep: d.current_step ?? undefined,
    stepsDone: d.steps_done,
    stepsTotal: d.steps_total,
    healStreak: d.heal_streak,
  };
}

// ── UI render helpers (pure, no hooks) ───────────────────────────────────────

export function statusPill(s: DeviceStatus): React.ReactElement {
  const map: Record<DeviceStatus, string> = {
    idle:    "bg-slate-500/15 text-slate-300 border-slate-500/30",
    running: "bg-blue-500/15 text-blue-300 border-blue-500/30 animate-pulse",
    booting: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    offline: "bg-slate-700/40 text-slate-500 border-slate-600/40",
    error:   "bg-red-500/15 text-red-300 border-red-500/30",
  };
  const label: Record<DeviceStatus, string> = {
    idle: "hazır", running: "çalışıyor", booting: "açılıyor", offline: "kapalı", error: "hata",
  };
  return React.createElement(
    "span",
    { className: `rounded-full border px-2 py-0.5 text-[10px] font-medium ${map[s]}` },
    label[s],
  );
}

export function platformBadge(p: Platform, os: string, kind: DeviceKind): React.ReactElement {
  const color = p === "ios" ? "text-slate-200" : "text-emerald-300";
  const icon  = p === "ios" ? "" : "🤖";
  const kindLabel = kind === "emulator" ? "emu" : kind === "simulator" ? "sim" : "fiz";
  return React.createElement(
    "span",
    { className: `inline-flex items-center gap-1 text-[11px] ${color}` },
    React.createElement("span", { className: "text-sm leading-none" }, icon),
    React.createElement("span", { className: "font-medium" }, `${p === "ios" ? "iOS" : "Android"} ${os}`),
    React.createElement(
      "span",
      { className: "rounded bg-slate-800 px-1 text-[9px] uppercase tracking-wide text-slate-400" },
      kindLabel,
    ),
  );
}
