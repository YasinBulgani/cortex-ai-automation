import type { Meta, StoryObj } from "@storybook/react";
import { Sparkline } from "./sparkline";

const meta: Meta<typeof Sparkline> = {
  title: "Primitives/Sparkline",
  component: Sparkline,
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "radio", options: ["line", "area", "bar"] },
  },
};

export default meta;
type Story = StoryObj<typeof Sparkline>;

const sample = [12, 18, 15, 22, 28, 25, 32];

export const Line: Story = {
  args: { data: sample, variant: "line", className: "text-emerald-400 h-8 w-32" },
};

export const Area: Story = {
  args: { data: sample, variant: "area", className: "text-blue-400 h-8 w-32" },
};

export const Bar: Story = {
  args: { data: sample, variant: "bar", className: "text-violet-400 h-8 w-32" },
};

export const Comparison: Story = {
  render: () => (
    <div className="grid grid-cols-3 gap-6">
      <div>
        <p className="text-xs text-slate-400 mb-2">Line</p>
        <Sparkline data={sample} variant="line" className="text-emerald-400 h-12 w-40" />
      </div>
      <div>
        <p className="text-xs text-slate-400 mb-2">Area</p>
        <Sparkline data={sample} variant="area" className="text-blue-400 h-12 w-40" />
      </div>
      <div>
        <p className="text-xs text-slate-400 mb-2">Bar</p>
        <Sparkline data={sample} variant="bar" className="text-violet-400 h-12 w-40" />
      </div>
    </div>
  ),
};

export const Trends: Story = {
  render: () => (
    <div className="space-y-2">
      <Sparkline data={[10, 15, 12, 18, 22, 25, 30]} variant="area" className="text-emerald-400 h-8 w-48" />
      <Sparkline data={[30, 28, 25, 20, 15, 12, 8]}  variant="area" className="text-red-400 h-8 w-48" />
      <Sparkline data={[20, 22, 18, 23, 21, 24, 22]} variant="area" className="text-amber-400 h-8 w-48" />
    </div>
  ),
};
