import type { Meta, StoryObj } from "@storybook/react";
import { Label, FieldHelp } from "./label";
import { Input } from "./input";

const meta: Meta<typeof Label> = {
  title: "Primitives/Label",
  component: Label,
  tags: ["autodocs"],
  argTypes: {
    required: { control: "boolean" },
    size:     { control: "radio", options: ["sm", "md"] },
  },
};

export default meta;
type Story = StoryObj<typeof Label>;

export const Default: Story = {
  args: { children: "E-posta" },
};

export const Required: Story = {
  args: { children: "Şifre", required: true },
};

export const WithDescription: Story = {
  args: {
    children: "Açıklama",
    description: "Maks 200 karakter; özetle açıkla.",
  },
};

export const FieldComposition: StoryObj<typeof Label> = {
  render: () => (
    <div className="max-w-sm">
      <Label htmlFor="email" required description="Onaylama linki gönderilecek">
        E-posta
      </Label>
      <Input id="email" type="email" placeholder="ad@neurex.io" className="mt-1" />
      <FieldHelp>Kayıtlı e-posta adresinizi kullanın.</FieldHelp>
    </div>
  ),
};

export const InvalidField: StoryObj<typeof Label> = {
  render: () => (
    <div className="max-w-sm">
      <Label htmlFor="tckn" required>T.C. Kimlik No</Label>
      <Input id="tckn" invalid defaultValue="123" className="mt-1" />
      <FieldHelp invalid>11 haneli olmalıdır.</FieldHelp>
    </div>
  ),
};
