import type { Meta, StoryObj } from "@storybook/react";
import { Divider } from "./divider";

const meta: Meta<typeof Divider> = {
  title: "Primitives/Divider",
  component: Divider,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Divider>;

export const Horizontal: Story = {
  render: () => (
    <div className="space-y-4 max-w-md">
      <p>Üstteki içerik</p>
      <Divider />
      <p>Alttaki içerik</p>
    </div>
  ),
};

export const Vertical: Story = {
  render: () => (
    <div className="flex h-16 items-center gap-3">
      <span>Sol</span>
      <Divider orientation="vertical" />
      <span>Orta</span>
      <Divider orientation="vertical" subtle />
      <span>Sağ</span>
    </div>
  ),
};

export const WithLabel: Story = {
  render: () => (
    <div className="max-w-md">
      <Divider label="VEYA" />
    </div>
  ),
};

export const Subtle: Story = {
  render: () => <Divider subtle />,
};
