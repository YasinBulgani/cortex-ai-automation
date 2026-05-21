import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Slider } from "./slider";

const meta: Meta<typeof Slider> = {
  title: "Primitives/Slider",
  component: Slider,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Slider>;

export const Default: Story = {
  render: () => (
    <div className="max-w-md">
      <Slider aria-label="volume" defaultValue={50} showValue />
    </div>
  ),
};

export const WithLabel: Story = {
  render: () => (
    <div className="max-w-md">
      <Slider label="Ses" defaultValue={70} showValue />
    </div>
  ),
};

export const PercentFormat: Story = {
  render: () => {
    function Demo() {
      const [v, setV] = useState(40);
      return (
        <div className="max-w-md">
          <Slider
            label="Threshold"
            value={v}
            onValueChange={setV}
            showValue
            formatValue={(x) => `${x}%`}
          />
        </div>
      );
    }
    return <Demo />;
  },
};

export const StepRange: Story = {
  render: () => (
    <div className="max-w-md space-y-3">
      <Slider label="0..10 step 1" defaultValue={5} min={0} max={10} step={1} showValue />
      <Slider label="0..100 step 5" defaultValue={25} step={5} showValue />
    </div>
  ),
};

export const Invalid: Story = {
  args: { "aria-label": "x", defaultValue: 80, invalid: true, showValue: true },
};
