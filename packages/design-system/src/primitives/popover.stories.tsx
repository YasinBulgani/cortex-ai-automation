import type { Meta, StoryObj } from "@storybook/react";
import { Popover } from "./popover";
import { Button } from "./button";

const meta: Meta<typeof Popover> = {
  title: "Primitives/Popover",
  component: Popover,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Popover>;

export const Default: Story = {
  render: () => (
    <Popover
      width="w-64"
      trigger={({ toggle, ref, ...rest }) => (
        <Button ref={ref as React.RefObject<HTMLButtonElement>} onClick={toggle} {...rest}>
          Popover aç
        </Button>
      )}
    >
      <p className="font-semibold">Bilgi</p>
      <p className="mt-1 text-fg-muted">
        Bu bir popover içeriği. ESC veya dışına tıkla → kapanır.
      </p>
    </Popover>
  ),
};

export const TopAligned: Story = {
  render: () => (
    <div className="flex h-72 items-end">
      <Popover
        side="top"
        align="start"
        trigger={({ toggle, ref, ...rest }) => (
          <Button ref={ref as React.RefObject<HTMLButtonElement>} variant="outline" onClick={toggle} {...rest}>
            Yukarı aç
          </Button>
        )}
      >
        Yukarıda görünür.
      </Popover>
    </div>
  ),
};
