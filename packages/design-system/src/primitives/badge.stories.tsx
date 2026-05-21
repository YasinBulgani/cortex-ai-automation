import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta: Meta<typeof Badge> = {
  title: "Primitives/Badge",
  component: Badge,
  tags: ["autodocs"],
  argTypes: {
    status: { control: "select", options: ["success", "warning", "danger", "info", "neutral"] },
    size:   { control: "radio", options: ["xs", "sm", "md"] },
    dot:    { control: "boolean" },
    interactive: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {
  args: { children: "Yeni", status: "info" },
};

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Badge status="success">Başarılı</Badge>
      <Badge status="warning">Uyarı</Badge>
      <Badge status="danger">Hata</Badge>
      <Badge status="info">Bilgi</Badge>
      <Badge status="neutral">Nötr</Badge>
    </div>
  ),
};

export const WithDot: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Badge dot status="success">Çalışıyor</Badge>
      <Badge dot status="warning">Bakım</Badge>
      <Badge dot status="danger">Kapalı</Badge>
    </div>
  ),
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-2">
      <Badge size="xs" status="info">XS</Badge>
      <Badge size="sm" status="info">SM</Badge>
      <Badge size="md" status="info">MD</Badge>
    </div>
  ),
};

export const Interactive: Story = {
  args: { children: "Tıklanabilir", interactive: true, status: "info" },
};
