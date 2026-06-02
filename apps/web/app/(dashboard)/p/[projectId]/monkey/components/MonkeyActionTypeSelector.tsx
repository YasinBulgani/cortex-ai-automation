"use client";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ActionType =
  | "click"
  | "input"
  | "scroll"
  | "navigate"
  | "resize"
  | "keypress";

export const ACTION_LABELS: Record<ActionType, string> = {
  click: "Rastgele Tıklama",
  input: "Rastgele Yazma",
  scroll: "Kaydırma",
  navigate: "Geri/İleri Gezinme",
  resize: "Pencere Boyutu Değiştirme",
  keypress: "Rastgele Tuş Basma",
};

export const ALL_ACTION_TYPES: ActionType[] = [
  "click",
  "input",
  "scroll",
  "navigate",
  "resize",
  "keypress",
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MonkeyActionTypeSelectorProps {
  selected: ActionType[];
  onChange: (updated: ActionType[]) => void;
  disabled?: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MonkeyActionTypeSelector({
  selected,
  onChange,
  disabled = false,
}: MonkeyActionTypeSelectorProps) {
  const toggle = (type: ActionType) => {
    if (disabled) return;
    if (selected.includes(type)) {
      onChange(selected.filter((t) => t !== type));
    } else {
      onChange([...selected, type]);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[11px] uppercase tracking-widest text-slate-500">
        Eylem Türleri
      </span>
      <div className="flex flex-wrap gap-1.5">
        {ALL_ACTION_TYPES.map((type) => {
          const active = selected.includes(type);
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggle(type)}
              disabled={disabled}
              className={[
                "rounded-lg border px-2.5 py-1 text-xs font-medium transition-all",
                active
                  ? "border-orange-400/40 bg-orange-500/15 text-orange-200"
                  : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200",
                disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
              ].join(" ")}
            >
              {ACTION_LABELS[type]}
            </button>
          );
        })}
      </div>
      {selected.length === 0 && (
        <p className="text-[11px] text-red-400 mt-0.5">
          En az bir eylem türü seçilmeli.
        </p>
      )}
    </div>
  );
}
