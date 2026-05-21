import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Tabs, TabPanel } from "./tabs";
import { Badge } from "./badge";

const meta: Meta<typeof Tabs> = {
  title: "Primitives/Tabs",
  component: Tabs,
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "radio", options: ["line", "pills"] },
    size:    { control: "radio", options: ["sm", "md"] },
  },
};

export default meta;
type Story = StoryObj<typeof Tabs>;

const items = [
  { value: "overview", label: "Genel" },
  { value: "config",   label: "Konfig", badge: <Badge size="xs" status="info">3</Badge> },
  { value: "logs",     label: "Loglar" },
  { value: "danger",   label: "Devre dışı", disabled: true },
];

function Demo({ variant = "line" }: { variant?: "line" | "pills" }) {
  const [active, setActive] = useState("overview");
  return (
    <div className="space-y-3">
      <Tabs items={items} value={active} onValueChange={setActive} variant={variant} label="Sekme demo" />
      <TabPanel value="overview" activeValue={active}>Bu genel sekmesi.</TabPanel>
      <TabPanel value="config"   activeValue={active}>Bu konfig sekmesi.</TabPanel>
      <TabPanel value="logs"     activeValue={active}>Bu log sekmesi.</TabPanel>
    </div>
  );
}

export const Line:  Story = { render: () => <Demo variant="line" /> };
export const Pills: Story = { render: () => <Demo variant="pills" /> };
