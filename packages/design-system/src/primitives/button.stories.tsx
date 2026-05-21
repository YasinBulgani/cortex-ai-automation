import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

const meta: Meta<typeof Button> = {
  title: "Primitives/Button",
  component: Button,
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "outline", "ghost", "subtle", "danger", "ghost-danger", "link"],
    },
    size: {
      control: "radio",
      options: ["xs", "sm", "md", "lg", "icon"],
    },
    loading:   { control: "boolean" },
    disabled:  { control: "boolean" },
    fullWidth: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Default: Story = {
  args: { children: "Kaydet" },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="subtle">Subtle</Button>
      <Button variant="danger">Danger</Button>
      <Button variant="ghost-danger">Ghost Danger</Button>
      <Button variant="link">Link</Button>
    </div>
  ),
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-end gap-3">
      <Button size="xs">XS</Button>
      <Button size="sm">SM</Button>
      <Button size="md">MD</Button>
      <Button size="lg">LG</Button>
      <Button size="icon">⚙</Button>
    </div>
  ),
};

export const Loading: Story = {
  args: { children: "Kaydediliyor…", loading: true },
};

export const WithIcons: Story = {
  render: () => (
    <div className="flex gap-3">
      <Button leadingIcon={<span>＋</span>}>Yeni</Button>
      <Button trailingIcon={<span>→</span>}>İlerle</Button>
      <Button variant="danger" leadingIcon={<span>🗑</span>}>Sil</Button>
    </div>
  ),
};

export const FullWidth: Story = {
  args: { children: "Tam Genişlik", fullWidth: true },
  parameters: { layout: "padded" },
};

export const Disabled: Story = {
  args: { children: "Pasif", disabled: true },
};
