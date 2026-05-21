import type { Meta, StoryObj } from "@storybook/react";
import { Kbd, KbdGroup } from "./kbd";

const meta: Meta<typeof Kbd> = {
  title: "Primitives/Kbd",
  component: Kbd,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Kbd>;

export const Default: Story = { args: { children: "K" } };

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Kbd size="sm">⌘</Kbd>
      <Kbd size="md">⌘</Kbd>
    </div>
  ),
};

export const Shortcuts: Story = {
  render: () => (
    <div className="flex flex-col gap-3 text-sm text-fg-muted">
      <div className="flex items-center gap-2">
        <KbdGroup><Kbd>⌘</Kbd><Kbd>K</Kbd></KbdGroup>
        <span>Komut paleti</span>
      </div>
      <div className="flex items-center gap-2">
        <KbdGroup><Kbd>⌘</Kbd><Kbd>⇧</Kbd><Kbd>P</Kbd></KbdGroup>
        <span>Proje ara</span>
      </div>
      <div className="flex items-center gap-2">
        <KbdGroup><Kbd>Ctrl</Kbd><Kbd>Z</Kbd></KbdGroup>
        <span>Geri al</span>
      </div>
    </div>
  ),
};
