import type { Meta, StoryObj } from "@storybook/react";
import { Tooltip } from "./tooltip";
import { Button } from "./button";

const meta: Meta<typeof Tooltip> = {
  title: "Primitives/Tooltip",
  component: Tooltip,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  render: () => (
    <div className="flex justify-center p-16">
      <Tooltip content="Bir ipucu metni">
        <Button variant="secondary" size="sm">Üzerine gel</Button>
      </Tooltip>
    </div>
  ),
};

export const Placements: Story = {
  render: () => (
    <div className="grid grid-cols-2 gap-8 p-16 place-items-center">
      {(["top", "bottom", "left", "right"] as const).map(p => (
        <Tooltip key={p} content={`Placement: ${p}`} placement={p} delay={0}>
          <Button variant="outline" size="sm">{p}</Button>
        </Tooltip>
      ))}
    </div>
  ),
};

export const WithShortcut: Story = {
  render: () => (
    <div className="flex justify-center p-16">
      <Tooltip content="Komut paleti" shortcut="⌘K" delay={0}>
        <Button variant="secondary" size="sm">Arama</Button>
      </Tooltip>
    </div>
  ),
};

export const Disabled: Story = {
  render: () => (
    <div className="flex justify-center p-16">
      <Tooltip content="Bu tooltip görünmez" disabled delay={0}>
        <Button variant="ghost" size="sm">Devre dışı</Button>
      </Tooltip>
    </div>
  ),
};
