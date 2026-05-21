import type { Meta, StoryObj } from "@storybook/react";
import { ActivityHeatmap } from "./activity-heatmap";

const meta: Meta<typeof ActivityHeatmap> = {
  title: "Patterns/ActivityHeatmap",
  component: ActivityHeatmap,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof ActivityHeatmap>;

function generateData(weeks = 26): { date: string; value: number }[] {
  const result = [];
  const today = new Date();
  for (let i = weeks * 7 - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const val = Math.random() > 0.4 ? Math.floor(Math.random() * 15) : 0;
    result.push({ date: d.toISOString().slice(0, 10), value: val });
  }
  return result;
}

export const Default: Story = {
  render: () => (
    <div className="max-w-3xl">
      <ActivityHeatmap data={generateData(26)} title="Test Koşuları" label="koşu" />
    </div>
  ),
};

export const HalfYear: Story = {
  render: () => (
    <div className="max-w-2xl">
      <ActivityHeatmap data={generateData(13)} weeks={13} title="Son 3 Ay" label="senaryo" />
    </div>
  ),
};

export const Empty: Story = {
  render: () => (
    <div className="max-w-xl">
      <ActivityHeatmap data={[]} weeks={8} title="Aktivite" label="aktivite" />
    </div>
  ),
};
