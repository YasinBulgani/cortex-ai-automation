import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Stepper } from "./stepper";
import { Button } from "./button";

const meta: Meta<typeof Stepper> = {
  title: "Primitives/Stepper",
  component: Stepper,
  tags: ["autodocs"],
  argTypes: {
    orientation: { control: "radio", options: ["horizontal", "vertical"] },
    active: { control: { type: "range", min: 0, max: 3, step: 1 } },
  },
};

export default meta;
type Story = StoryObj<typeof Stepper>;

const steps = [
  { key: "1", title: "Hesap",   description: "E-posta + şifre" },
  { key: "2", title: "Profil",  description: "Ad, fotoğraf" },
  { key: "3", title: "Plan",    description: "Faturalama" },
  { key: "4", title: "Bitir",   description: "Onayla" },
];

export const Horizontal: Story = {
  render: () => <Stepper steps={steps} active={1} />,
};

export const Vertical: Story = {
  render: () => <Stepper steps={steps} active={2} orientation="vertical" />,
};

export const WithError: Story = {
  render: () => {
    const withErr = [
      { key: "1", title: "Hesap", status: "complete" as const },
      { key: "2", title: "Profil", status: "error" as const, description: "Geçersiz alan" },
      { key: "3", title: "Plan" },
    ];
    return <Stepper steps={withErr} active={1} />;
  },
};

export const Clickable: Story = {
  render: () => {
    function Demo() {
      const [active, setActive] = useState(1);
      return (
        <div className="space-y-4">
          <Stepper steps={steps} active={active} onStepClick={i => setActive(i)} />
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setActive(a => Math.max(0, a - 1))}>← Geri</Button>
            <Button size="sm" onClick={() => setActive(a => Math.min(steps.length - 1, a + 1))}>İleri →</Button>
          </div>
        </div>
      );
    }
    return <Demo />;
  },
};
