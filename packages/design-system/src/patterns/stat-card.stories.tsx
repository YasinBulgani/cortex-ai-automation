import type { Meta, StoryObj } from "@storybook/react";
import { StatCard } from "./stat-card";

const meta: Meta<typeof StatCard> = {
  title: "Patterns/StatCard",
  component: StatCard,
  tags: ["autodocs"],
  argTypes: {
    tone: { control: "select", options: ["default", "success", "warning", "danger", "brand", "info", "ai"] },
  },
};

export default meta;
type Story = StoryObj<typeof StatCard>;

const trend = [10, 12, 11, 15, 18, 17, 20];

export const Default: Story = {
  args: { label: "Toplam Senaryo", value: 1614, sparkline: trend },
};

export const WithTrend: Story = {
  args: {
    label: "Geçme Oranı",
    value: "%94",
    tone: "success",
    trend: +5,
    sparkline: [80, 82, 85, 88, 90, 92, 94],
    hint: "son 7 gün",
  },
};

export const Loading: Story = {
  args: { label: "Hesaplanıyor", value: "—", loading: true },
};

export const AllTones: Story = {
  render: () => (
    <div className="grid grid-cols-3 gap-4 max-w-3xl">
      <StatCard label="Default" value="100"   sparkline={trend} />
      <StatCard label="Success" value="%94"   tone="success" sparkline={trend} trend={+2} />
      <StatCard label="Warning" value="3"     tone="warning" hint="aksiyon gerek" />
      <StatCard label="Danger"  value="12"    tone="danger" trend={-15} />
      <StatCard label="Brand"   value="2.3K"  tone="brand" sparkline={trend} />
      <StatCard label="Info"    value="383"   tone="info" sparkline={trend} />
      <StatCard label="AI"      value="1.2M"  tone="ai" hint="token / ay" />
    </div>
  ),
};
