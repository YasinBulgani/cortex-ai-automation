import type { Meta, StoryObj } from "@storybook/react";
import { Skeleton, SkeletonText, SkeletonCard } from "./skeleton";

const meta: Meta<typeof Skeleton> = {
  title: "Primitives/Skeleton",
  component: Skeleton,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Skeleton>;

export const Rect: Story = { args: { className: "h-6 w-40" } };
export const Circle: Story = { args: { shape: "circle", className: "h-10 w-10" } };
export const Text: Story = { args: { shape: "text" } };

export const TextBlock: Story = {
  render: () => <SkeletonText lines={5} />,
};

export const CardWithAvatar: Story = {
  render: () => <SkeletonCard withAvatar className="max-w-sm" />,
};

export const Grid: Story = {
  render: () => (
    <div className="grid grid-cols-3 gap-3 max-w-2xl">
      <SkeletonCard />
      <SkeletonCard />
      <SkeletonCard />
    </div>
  ),
};
