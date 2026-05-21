import type { Meta, StoryObj } from "@storybook/react";
import { Breadcrumb } from "./breadcrumb";

const meta: Meta<typeof Breadcrumb> = {
  title: "Primitives/Breadcrumb",
  component: Breadcrumb,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Breadcrumb>;

export const Default: Story = {
  render: () => (
    <Breadcrumb
      items={[
        { label: "Ana",      href: "/" },
        { label: "Projeler", href: "/p" },
        { label: "Müşteri Portalı", href: "/p/portal" },
        { label: "Senaryolar" },
      ]}
    />
  ),
};

export const ChevronSeparator: Story = {
  render: () => (
    <Breadcrumb
      separator="›"
      items={[
        { label: "Ana",     href: "/" },
        { label: "Ayarlar", href: "/s" },
        { label: "Profil" },
      ]}
    />
  ),
};

export const Collapsed: Story = {
  render: () => (
    <Breadcrumb
      maxItems={4}
      items={[
        { label: "Ana",     href: "/" },
        { label: "L1",      href: "/1" },
        { label: "L2",      href: "/1/2" },
        { label: "L3",      href: "/1/2/3" },
        { label: "L4",      href: "/1/2/3/4" },
        { label: "Mevcut" },
      ]}
    />
  ),
};
