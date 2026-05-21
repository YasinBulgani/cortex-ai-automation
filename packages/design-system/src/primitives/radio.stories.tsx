import type { Meta, StoryObj } from "@storybook/react";
import { Radio, RadioGroup } from "./radio";

const meta: Meta<typeof Radio> = {
  title: "Primitives/Radio",
  component: Radio,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Radio>;

const options = [
  { value: "tr", label: "Türkçe", description: "Türkiye lokasyonu" },
  { value: "en", label: "English", description: "Default" },
  { value: "ar", label: "العربية", description: "RTL" },
];

export const Single: Story = {
  args: { name: "x", value: "a", label: "Tek opsiyon" },
};

export const Group: StoryObj<typeof Radio> = {
  render: () => <RadioGroup name="lang" options={options} defaultValue="tr" />,
};

export const Horizontal: StoryObj<typeof Radio> = {
  render: () => (
    <RadioGroup
      name="density"
      orientation="horizontal"
      options={[
        { value: "compact", label: "Kompakt" },
        { value: "normal",  label: "Normal" },
        { value: "spacious",label: "Geniş" },
      ]}
      defaultValue="normal"
    />
  ),
};
