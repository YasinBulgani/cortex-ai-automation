/**
 * Stories for the Onboarding Wizard step progress indicator.
 */

import type { Meta, StoryObj } from "@storybook/react";
import React, { useState } from "react";

const STEPS = [
  { id: 1, title: "Profil",          icon: "👤" },
  { id: 2, title: "İlk Proje",       icon: "📁" },
  { id: 3, title: "API Spec",        icon: "📄" },
  { id: 4, title: "AI Tercih",       icon: "🤖" },
  { id: 5, title: "Test Yönetimi",   icon: "🧪" },
  { id: 6, title: "Hazır!",          icon: "🚀" },
];

function StepProgress({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {STEPS.map((s, i) => (
        <div key={s.id} className="flex items-center gap-1.5 flex-1 last:flex-none">
          <div
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold transition-all ${
              s.id < current
                ? "bg-emerald-500 text-white"
                : s.id === current
                  ? "bg-violet-600 text-white ring-4 ring-violet-500/30"
                  : "bg-slate-800 text-slate-500"
            }`}
          >
            {s.id < current ? "✓" : s.id}
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={`h-0.5 flex-1 rounded-full transition-all ${
                s.id < current ? "bg-emerald-500" : "bg-slate-800"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function InteractiveDemo() {
  const [current, setCurrent] = useState(1);
  return (
    <div className="space-y-4 w-full max-w-md">
      <StepProgress current={current} />
      <div className="flex gap-2">
        <button
          onClick={() => setCurrent((c) => Math.max(1, c - 1))}
          disabled={current <= 1}
          className="flex-1 rounded border border-slate-700 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30"
        >
          ← Geri
        </button>
        <button
          onClick={() => setCurrent((c) => Math.min(STEPS.length, c + 1))}
          disabled={current >= STEPS.length}
          className="flex-1 rounded bg-violet-600 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-30"
        >
          Devam →
        </button>
      </div>
      <p className="text-center text-xs text-slate-500">
        Adım {current} / {STEPS.length} — {STEPS[current - 1].icon} {STEPS[current - 1].title}
      </p>
    </div>
  );
}

const meta: Meta<typeof StepProgress> = {
  title: "App / OnboardingStepProgress",
  component: StepProgress,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="bg-slate-950 p-8 flex items-center justify-center">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    current: {
      control: { type: "range", min: 1, max: 6, step: 1 },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StepProgress>;

export const Step1: Story = { args: { current: 1 } };
export const Step3: Story = { args: { current: 3 } };
export const Step5: Story = { args: { current: 5 } };
export const Complete: Story = { args: { current: 7 } };

export const Interactive: Story = {
  render: () => <InteractiveDemo />,
};
