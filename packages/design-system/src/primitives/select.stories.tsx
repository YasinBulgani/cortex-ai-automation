import type { Meta, StoryObj } from "@storybook/react";
import { Select } from "./select";

const meta: Meta<typeof Select> = {
  title: "Primitives/Select",
  component: Select,
  tags: ["autodocs"],
  argTypes: {
    selectSize: { control: "radio", options: ["sm", "md", "lg"] },
    invalid:    { control: "boolean" },
    disabled:   { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Select>;

const options = [
  { value: "tr", label: "Türkçe" },
  { value: "en", label: "English" },
  { value: "ar", label: "العربية" },
];

export const Default: Story = {
  args: { options, placeholder: "Dil seç" },
};

export const Sizes: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-sm">
      <Select selectSize="sm" options={options} defaultValue="tr" />
      <Select selectSize="md" options={options} defaultValue="en" />
      <Select selectSize="lg" options={options} defaultValue="ar" />
    </div>
  ),
};

export const Invalid: Story = {
  args: { options, invalid: true, defaultValue: "tr" },
};

export const Disabled: Story = {
  args: { options, disabled: true, defaultValue: "tr" },
};
