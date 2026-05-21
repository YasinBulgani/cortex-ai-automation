import type { Meta, StoryObj } from "@storybook/react";
import { Switch } from "./switch";

const meta: Meta<typeof Switch> = {
  title: "Primitives/Switch",
  component: Switch,
  tags: ["autodocs"],
  argTypes: {
    switchSize: { control: "radio", options: ["sm", "md"] },
    disabled:   { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Switch>;

export const Default: Story = {
  args: { label: "Bildirimler aktif" },
};

export const Checked: Story = {
  args: { label: "Dark mode", defaultChecked: true },
};

export const Disabled: Story = {
  args: { label: "Pasif", disabled: true },
};

export const Sizes: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <Switch switchSize="sm" label="Small" />
      <Switch switchSize="md" label="Medium" defaultChecked />
    </div>
  ),
};
