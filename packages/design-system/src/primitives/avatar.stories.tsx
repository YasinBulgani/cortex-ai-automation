import type { Meta, StoryObj } from "@storybook/react";
import { Avatar, AvatarGroup } from "./avatar";

const meta: Meta<typeof Avatar> = {
  title: "Primitives/Avatar",
  component: Avatar,
  tags: ["autodocs"],
  argTypes: {
    size: {
      control: "radio",
      options: ["xs", "sm", "md", "lg", "xl"],
    },
    shape: {
      control: "radio",
      options: ["circle", "rounded", "square"],
    },
    status: {
      control: "select",
      options: [undefined, "online", "away", "busy", "offline"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Avatar>;

export const Default: Story = {
  args: {
    name: "Yasin Bulgan",
    size: "md",
    shape: "rounded",
  },
};

export const WithImage: Story = {
  args: {
    name: "Yasin Bulgan",
    src: "https://i.pravatar.cc/150?img=12",
    size: "lg",
    shape: "circle",
  },
};

export const WithStatus: Story = {
  args: {
    name: "Ayşe Kaya",
    size: "lg",
    shape: "circle",
    status: "online",
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-end gap-3">
      <Avatar name="XS" size="xs" />
      <Avatar name="SM" size="sm" />
      <Avatar name="MD" size="md" />
      <Avatar name="LG" size="lg" />
      <Avatar name="XL" size="xl" />
    </div>
  ),
};

export const AllShapes: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <Avatar name="Circle"  shape="circle"  size="lg" />
      <Avatar name="Rounded" shape="rounded" size="lg" />
      <Avatar name="Square"  shape="square"  size="lg" />
    </div>
  ),
};

export const Group: Story = {
  render: () => (
    <AvatarGroup max={3}>
      <Avatar name="Yasin Bulgan" size="sm" shape="circle" />
      <Avatar name="Ayşe Kaya"    size="sm" shape="circle" />
      <Avatar name="Mehmet Demir" size="sm" shape="circle" />
      <Avatar name="Fatma Yılmaz" size="sm" shape="circle" />
      <Avatar name="Ali Veli"     size="sm" shape="circle" />
    </AvatarGroup>
  ),
};
