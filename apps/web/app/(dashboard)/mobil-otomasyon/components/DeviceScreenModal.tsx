"use client";

type Platform = "android" | "ios";
type DeviceKind = "emulator" | "simulator" | "physical";
type DeviceStatus = "idle" | "running" | "booting" | "offline" | "error";

type Device = {
  id: string;
  name: string;
  platform: Platform;
  osVersion: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpuPct: number;
  ramPct: number;
  appiumPort: number;
  currentStep?: string;
  stepsDone: number;
  stepsTotal: number;
  healStreak: number;
};

export interface DeviceScreenModalProps {
  device: Device;
  onClose: () => void;
}

export function DeviceScreenModal({ device, onClose }: DeviceScreenModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-full max-w-md flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-white">{device.name}</p>
            <p className="text-[10px] text-slate-500">
              {device.platform === "ios" ? "iOS" : "Android"} {device.osVersion} · {device.profile} · :{device.appiumPort}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
          >
            ✕ Kapat
          </button>
        </div>

        {/* Device Frame */}
        <div className="flex-1 overflow-auto bg-slate-900/40 p-6">
          <div className="relative mx-auto w-[280px]">
            {/* Phone bezel */}
            <div className="rounded-[40px] border-4 border-slate-800 bg-slate-950 p-2 shadow-[0_0_60px_rgba(124,58,237,0.15)]">
              {/* Notch */}
              <div className="relative mx-auto h-5 w-24 -translate-y-0.5 rounded-b-2xl bg-slate-950 z-10" />
              {/* Screen */}
              <div className="relative aspect-[9/19.5] overflow-hidden rounded-[28px] bg-gradient-to-b from-slate-900 to-slate-950">
                {/* Status bar */}
                <div className="flex items-center justify-between bg-slate-900/80 px-4 py-2 text-[10px] text-slate-300">
                  <span>{new Date().toTimeString().slice(0, 5)}</span>
                  <span className="flex items-center gap-1">📶 📶 🔋{device.battery}%</span>
                </div>
                {/* Mock App Content */}
                <div className="flex h-full flex-col items-center justify-center px-4 text-center text-white">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/20 text-3xl">
                    📱
                  </div>
                  <p className="text-sm font-semibold">{device.status === "running" ? "Test Koşuyor" : "Cihaz Hazır"}</p>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {device.status === "running"
                      ? `${device.stepsDone}/${device.stepsTotal} adım`
                      : "Otomasyon başlatın"}
                  </p>
                  {device.status === "running" && device.currentStep && (
                    <p className="mt-3 rounded-lg bg-slate-800/60 px-3 py-1.5 text-[10px] font-mono text-violet-200">
                      {device.currentStep}
                    </p>
                  )}
                  <div className="mt-6 grid grid-cols-3 gap-2 w-full max-w-[200px]">
                    {["💬", "📷", "🎮", "🛒", "📧", "⚙️"].map((emoji, i) => (
                      <div key={i} className="aspect-square flex items-center justify-center rounded-xl bg-slate-800/50 text-2xl">
                        {emoji}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Home indicator */}
            <div className="mx-auto mt-3 h-1 w-24 rounded-full bg-slate-700" />
          </div>
        </div>

        {/* Footer info */}
        <div className="border-t border-slate-800 bg-slate-900/40 px-4 py-3">
          <p className="text-[11px] text-amber-200/80">
            ⚠️ Bu mock bir görünümdür. Gerçek ekran mirroring için Appium Inspector veya scrcpy kullanın.
          </p>
          <p className="mt-1 text-[10px] text-slate-500 font-mono">
            Appium: http://127.0.0.1:{device.appiumPort}
          </p>
        </div>
      </div>
    </div>
  );
}
