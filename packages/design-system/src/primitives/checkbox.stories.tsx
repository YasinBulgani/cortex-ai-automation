import type { Meta, StoryObj } from "@storybook/react";
import { Checkbox } from "./checkbox";

const meta: Meta<typeof Checkbox> = {
  title: "Primitives/Checkbox",
  component: Checkbox,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Checkbox>;

export const Default: Story = {
  args: { label: "Şartları kabul ediyorum" },
};

export const WithDescription: Story = {
  args: {
    label: "Pazarlama e-postaları al",
    description: "Aylık bülten + ürün duyuruları. İstediğinde kapatabilirsin.",
  },
};

export const Indeterminate: Story = {
  args: { label: "Tümünü seç", indeterminate: true },
};

export const Invalid: Story = {
  args: { label: "Kabul gerekli", invalid: true },
};

export const Disabled: Story = {
  args: { label: "Pasif", disabled: true, defaultChecked: true },
};

export const Group: Story = {
  render: () => (
    <div className="flex flex-col gap-2">
      <Checkbox label="Türkçe arayüz" defaultChecked />
      <Checkbox label="A/B testleri" />
      <Checkbox label="Deneysel özellikler" description="Beta — kararsız olabilir" />
    </div>
  ),
};
