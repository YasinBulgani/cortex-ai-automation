"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";
import type { Platform } from "./types";

/**
 * Modal form for enrolling a physical device into the Neurex device farm.
 * In mock mode (no backend), adds the device to local UI state only.
 */
export function PhysicalEnrollForm({
  onSubmitted,
  backendMode,
}: {
  onSubmitted: (name: string) => void;
  backendMode: "probing" | "connected" | "mock";
}) {
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState<Platform>("android");
  const [udid, setUdid] = useState("");
  const [osVersion, setOsVersion] = useState("14");
  const [appiumUrl, setAppiumUrl] = useState("http://lab-node-1.bgts.internal:4750");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || !udid.trim()) {
      setErr("Cihaz adı ve UDID/Serial zorunlu");
      return;
    }
    setErr(null);
    setSubmitting(true);
    try {
      if (backendMode === "connected") {
        await apiFetch("/api/v1/mobile/enroll-physical", {
          method: "POST",
          json: {
            name: name.trim(),
            platform,
            os_version: osVersion.trim(),
            udid: udid.trim(),
            appium_url: appiumUrl.trim(),
            profile: name.toLowerCase().replace(/\s+/g, "_"),
          },
        });
      } else {
        // Mock mod — 600ms bekle
        await new Promise((r) => setTimeout(r, 600));
      }
      onSubmitted(name);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Kayıt başarısız");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Cihaz Adı</label>
          <Input
            placeholder="Samsung S24 - Lab-01"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Platform</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value as Platform)}
            className="h-10 w-full rounded border border-slate-800 bg-slate-900 px-3 text-sm"
          >
            <option value="android">Android</option>
            <option value="ios">iOS</option>
          </select>
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">UDID / Serial</label>
          <Input
            placeholder="R58M3..."
            value={udid}
            onChange={(e) => setUdid(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">OS Version</label>
          <Input
            placeholder="14"
            value={osVersion}
            onChange={(e) => setOsVersion(e.target.value)}
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-[11px] text-slate-400 mb-1">Appium Server URL</label>
          <Input
            placeholder="http://lab-node-1.bgts.internal:4750"
            value={appiumUrl}
            onChange={(e) => setAppiumUrl(e.target.value)}
          />
        </div>
      </div>

      <div className="rounded-md border border-slate-800 bg-slate-900/40 p-3 space-y-1.5">
        <p className="text-[11px] font-semibold text-slate-300">Bir sonraki adımlar</p>
        <ol className="list-decimal list-inside text-[11px] text-slate-400 space-y-0.5">
          <li>Cihaz USB hub&apos;a takılı ve powered mı? (Cambrionix PowerPad veya muadili)</li>
          <li>ADB/WDA handshake testi otomatik çalışacak.</li>
          <li>MDM profili yüklenecek (Jamf iOS / Headwind Android).</li>
          <li>Kiosk mode etkinleştirilecek — cihaz yalnız test için.</li>
        </ol>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}

      <div className="flex items-center justify-end gap-2 pt-1">
        <span className="text-[10px] text-slate-500 mr-auto">
          {backendMode === "connected"
            ? "→ POST /api/v1/mobile/enroll-physical"
            : "Mock mod: yalnız UI'ya eklenir"}
        </span>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onSubmitted("")}
          disabled={submitting}
        >
          Vazgeç
        </Button>
        <Button type="button" onClick={submit} disabled={submitting}>
          {submitting ? "Kaydediliyor…" : "Kaydet & Handshake Yap"}
        </Button>
      </div>
    </>
  );
}
