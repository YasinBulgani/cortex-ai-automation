import type { Meta, StoryObj } from "@storybook/react";
import { Spinner } from "./spinner";

const meta: Meta<typeof Spinner> = {
  title: "Primitives/Spinner",
  component: Spinner,
  tags: ["autodocs"],
  argTypes: {
    size: { control: "radio", options: ["xs", "sm", "md", "lg"] },
  },
};

export default meta;
type Story = StoryObj<typeof Spinner>;

export const Default: Story = { args: {} };

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-end gap-4">
      <Spinner size="xs" />
      <Spinner size="sm" />
      <Spinner size="md" />
      <Spinner size="lg" />
    </div>
  ),
};

export const Decorative: Story = {
  args: { label: null, size: "md" },
};

export const Colored: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Spinner className="text-brand-primary" />
      <Spinner className="text-success" />
      <Spinner className="text-warning" />
      <Spinner className="text-danger" />
    </div>
  ),
};
