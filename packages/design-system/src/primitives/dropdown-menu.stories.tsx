import type { Meta, StoryObj } from "@storybook/react";
import { DropdownMenu, type DropdownEntry } from "./dropdown-menu";
import { Button } from "./button";

const meta: Meta<typeof DropdownMenu> = {
  title: "Primitives/DropdownMenu",
  component: DropdownMenu,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof DropdownMenu>;

const items: DropdownEntry[] = [
  { key: "h", heading: "İşlemler" },
  { key: "edit",   label: "Düzenle",   shortcut: "⌘E" },
  { key: "copy",   label: "Kopyala",   shortcut: "⌘C" },
  { key: "rename", label: "Yeniden adlandır" },
  { key: "s1", separator: true },
  { key: "export", label: "Dışa aktar" },
  { key: "share",  label: "Paylaş",    disabled: true },
  { key: "s2", separator: true },
  { key: "delete", label: "Sil", danger: true, shortcut: "⌫" },
];

export const Default: Story = {
  render: () => (
    <DropdownMenu
      items={items}
      trigger={({ toggle, ...rest }) => (
        <Button onClick={toggle} {...rest}>İşlemler ▾</Button>
      )}
    />
  ),
};

export const AlignEnd: Story = {
  render: () => (
    <div className="flex justify-end p-6">
      <DropdownMenu
        align="end"
        items={items}
        trigger={({ toggle, ...rest }) => (
          <Button variant="outline" size="sm" onClick={toggle} {...rest}>⋯</Button>
        )}
      />
    </div>
  ),
};

export const TopSide: Story = {
  render: () => (
    <div className="flex h-72 items-end">
      <DropdownMenu
        side="top"
        items={items}
        trigger={({ toggle, ...rest }) => (
          <Button variant="subtle" onClick={toggle} {...rest}>Yukarı açılır</Button>
        )}
      />
    </div>
  ),
};
