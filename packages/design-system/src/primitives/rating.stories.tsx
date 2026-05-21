import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Rating } from "./rating";

const meta: Meta<typeof Rating> = {
  title: "Primitives/Rating",
  component: Rating,
  tags: ["autodocs"],
  argTypes: {
    size: { control: "radio", options: ["sm", "md", "lg"] },
    readOnly: { control: "boolean" },
    disabled: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Rating>;

export const Default: Story = { args: { defaultValue: 3 } };

export const Sizes: Story = {
  render: () => (
    <div className="flex flex-col items-start gap-3">
      <Rating defaultValue={4} size="sm" />
      <Rating defaultValue={4} size="md" />
      <Rating defaultValue={4} size="lg" />
    </div>
  ),
};

export const ReadOnly: Story = { args: { value: 4, readOnly: true } };

export const Disabled: Story = { args: { value: 3, disabled: true } };

export const Controlled: Story = {
  render: () => {
    function Demo() {
      const [v, setV] = useState(0);
      return (
        <div className="flex items-center gap-3">
          <Rating value={v} onValueChange={setV} />
          <span className="text-sm text-fg-muted">Puan: {v}</span>
        </div>
      );
    }
    return <Demo />;
  },
};

export const CustomMax: Story = { args: { defaultValue: 6, max: 10 } };
