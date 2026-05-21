import type { Meta, StoryObj } from "@storybook/react";
import { Input, Textarea } from "./input";

const meta: Meta<typeof Input> = {
  title: "Primitives/Input",
  component: Input,
  tags: ["autodocs"],
  argTypes: {
    inputSize: { control: "radio", options: ["sm", "md", "lg"] },
    invalid:   { control: "boolean" },
    disabled:  { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = {
  args: { placeholder: "E-posta adresi" },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-md">
      <Input inputSize="sm" placeholder="Small" />
      <Input inputSize="md" placeholder="Medium" />
      <Input inputSize="lg" placeholder="Large" />
    </div>
  ),
};

export const Invalid: Story = {
  args: { invalid: true, placeholder: "geçersiz@", defaultValue: "x" },
};

export const WithIcons: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-md">
      <Input
        placeholder="Ara…"
        leadingIcon={<span aria-hidden>🔍</span>}
      />
      <Input
        placeholder="Şifre"
        type="password"
        trailingIcon={<span aria-hidden>👁</span>}
      />
    </div>
  ),
};

export const Disabled: Story = {
  args: { placeholder: "Pasif alan", disabled: true },
};

export const TextareaDefault: StoryObj<typeof Textarea> = {
  render: (args) => <Textarea {...args} />,
  args: { placeholder: "Notlar…", rows: 5 },
};
