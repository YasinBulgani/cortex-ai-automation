import type { Meta, StoryObj } from "@storybook/react";
import { Alert } from "./alert";

const meta: Meta<typeof Alert> = {
  title: "Primitives/Alert",
  component: Alert,
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "select", options: ["info", "success", "warning", "danger"] },
  },
};

export default meta;
type Story = StoryObj<typeof Alert>;

export const Info: Story = {
  args: { variant: "info", children: "Yeni bir özellik kullanıma sunuldu." },
};

export const SuccessWithTitle: Story = {
  args: {
    variant: "success",
    title: "Kaydedildi",
    children: "Tüm değişiklikler başarıyla saklandı.",
  },
};

export const WarningWithIcon: Story = {
  args: {
    variant: "warning",
    title: "Bakım uyarısı",
    icon: <span>⚠</span>,
    children: "Bu akşam 23:00 — 23:30 arası kısa kesinti planlandı.",
  },
};

export const DangerDismissable: Story = {
  args: {
    variant: "danger",
    title: "Hata",
    children: "Ödeme alınamadı. Lütfen kart bilgilerini kontrol et.",
    onClose: () => {},
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-3 max-w-2xl">
      <Alert variant="info"   title="Bilgi">Düz bilgilendirme mesajı.</Alert>
      <Alert variant="success" title="Başarı">İşlem tamam.</Alert>
      <Alert variant="warning" title="Uyarı">Dikkat gereken bir durum.</Alert>
      <Alert variant="danger"  title="Hata">İşlem başarısız.</Alert>
    </div>
  ),
};
