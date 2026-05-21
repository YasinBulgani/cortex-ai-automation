import type { Meta, StoryObj } from "@storybook/react";
import { Card, CardHeader, CardBody, CardFooter } from "./card";
import { Button } from "./button";
import { Badge } from "./badge";

const meta: Meta<typeof Card> = {
  title: "Primitives/Card",
  component: Card,
  tags: ["autodocs"],
  argTypes: {
    interactive: { control: "boolean" },
    compact:     { control: "boolean" },
    borderless:  { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    children: <span>İçerik buraya gelir.</span>,
  },
};

export const WithHeaderAndFooter: Story = {
  render: () => (
    <Card>
      <CardHeader
        title="Test Senaryosu #42"
        description="Login akışı — happy path"
        action={<Badge dot status="success">Aktif</Badge>}
      />
      <CardBody>
        Bu senaryonun açıklaması burada görüntülenir. Adım sayısı, son
        çalıştırılma zamanı ve sahibi gibi bilgiler eklenebilir.
      </CardBody>
      <CardFooter>
        <Button variant="ghost" size="sm">Düzenle</Button>
        <Button size="sm">Çalıştır</Button>
      </CardFooter>
    </Card>
  ),
};

export const InteractiveGrid: Story = {
  render: () => (
    <div className="grid grid-cols-3 gap-3 max-w-3xl">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} interactive compact>
          <CardHeader title={`Proje ${i + 1}`} description="2 senaryo" />
          <CardBody>Son koşu: 3 saat önce</CardBody>
        </Card>
      ))}
    </div>
  ),
};

export const Borderless: Story = {
  args: { borderless: true, children: <span>Kenarsız kart</span> },
};
