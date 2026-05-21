import type { Meta, StoryObj } from "@storybook/react";
import { Progress } from "./progress";

const meta: Meta<typeof Progress> = {
  title: "Primitives/Progress",
  component: Progress,
  tags: ["autodocs"],
  argTypes: {
    size:   { control: "radio", options: ["sm", "md", "lg"] },
    status: { control: "select", options: ["default", "success", "warning", "danger"] },
    value:  { control: { type: "range", min: 0, max: 100, step: 1 } },
  },
};

export default meta;
type Story = StoryObj<typeof Progress>;

export const Default: Story = { args: { value: 65, label: "yükleme" } };

export const Indeterminate: Story = { args: { label: "bekleniyor" } };

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-sm">
      <Progress size="sm" value={40} />
      <Progress size="md" value={60} />
      <Progress size="lg" value={80} />
    </div>
  ),
};

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-sm">
      <Progress value={70} status="default" />
      <Progress value={100} status="success" />
      <Progress value={50} status="warning" />
      <Progress value={30} status="danger" />
    </div>
  ),
};
