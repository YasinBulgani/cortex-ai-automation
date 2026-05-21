import type { Meta, StoryObj } from "@storybook/react";
import { EmptyState } from "./empty-state";
import { Button } from "./button";

const meta: Meta<typeof EmptyState> = {
  title: "Primitives/EmptyState",
  component: EmptyState,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const Default: Story = {
  args: {
    title: "Henüz senaryo yok",
    description: "İlk test senaryonuzu oluşturun.",
    action: <Button size="sm">Senaryo Ekle</Button>,
  },
};

export const WithIcon: Story = {
  args: {
    icon: <span className="text-2xl">📭</span>,
    title: "Sonuç bulunamadı",
    description: "Farklı filtreler deneyin.",
  },
};

export const Compact: Story = {
  render: () => (
    <div className="border rounded-lg">
      <EmptyState
        variant="compact"
        icon={<span>🔍</span>}
        title="Eşleşme yok"
        description="Arama kriterlerini değiştirin"
        action={<Button size="sm" variant="ghost">Temizle</Button>}
      />
    </div>
  ),
};

export const Hero: Story = {
  args: {
    variant: "hero",
    icon: <span className="text-4xl">🚀</span>,
    title: "Projeye hoş geldiniz",
    description: "Otomasyon yolculuğunuza ilk senaryo ile başlayın.",
    action: <Button>İlk Senaryonu Oluştur</Button>,
  },
};
