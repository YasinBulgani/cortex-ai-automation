import type { Meta, StoryObj } from "@storybook/react";
import { Toolbar, ToolbarSeparator, ToolbarGroup } from "./toolbar";
import { Button } from "./button";

const meta: Meta<typeof Toolbar> = {
  title: "Primitives/Toolbar",
  component: Toolbar,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Toolbar>;

export const Basic: Story = {
  render: () => (
    <Toolbar label="Düzenleyici">
      <Button size="icon" variant="ghost" aria-label="Bold">B</Button>
      <Button size="icon" variant="ghost" aria-label="Italic">I</Button>
      <Button size="icon" variant="ghost" aria-label="Underline">U</Button>
      <ToolbarSeparator />
      <Button size="icon" variant="ghost" aria-label="Link">🔗</Button>
      <Button size="icon" variant="ghost" aria-label="Code">{"</>"}</Button>
    </Toolbar>
  ),
};

export const Grouped: Story = {
  render: () => (
    <Toolbar label="Düzen + hizalama">
      <ToolbarGroup label="Stil">
        <Button size="icon" variant="ghost" aria-label="B">B</Button>
        <Button size="icon" variant="ghost" aria-label="I">I</Button>
      </ToolbarGroup>
      <ToolbarSeparator />
      <ToolbarGroup label="Hizalama">
        <Button size="icon" variant="ghost" aria-label="Sol">⬅</Button>
        <Button size="icon" variant="ghost" aria-label="Orta">⬌</Button>
        <Button size="icon" variant="ghost" aria-label="Sağ">➡</Button>
      </ToolbarGroup>
    </Toolbar>
  ),
};

export const Vertical: Story = {
  render: () => (
    <Toolbar orientation="vertical" label="Vertikal">
      <Button size="icon" variant="ghost" aria-label="Crop">✂</Button>
      <Button size="icon" variant="ghost" aria-label="Rotate">↻</Button>
      <ToolbarSeparator orientation="horizontal" />
      <Button size="icon" variant="ghost" aria-label="Save">💾</Button>
    </Toolbar>
  ),
};
