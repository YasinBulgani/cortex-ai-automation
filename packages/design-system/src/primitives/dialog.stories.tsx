import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Dialog } from "./dialog";
import { Button } from "./button";
import { Input } from "./input";
import { Label } from "./label";

const meta: Meta<typeof Dialog> = {
  title: "Primitives/Dialog",
  component: Dialog,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Dialog>;

function Demo({ size = "md" }: { size?: "sm" | "md" | "lg" | "xl" | "full" }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Aç</Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Senaryoyu sil"
        description="Bu işlem geri alınamaz."
        size={size}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>İptal</Button>
            <Button variant="danger" onClick={() => setOpen(false)}>Sil</Button>
          </>
        }
      >
        <p>Seçili 3 senaryo kalıcı olarak silinecek. Onaylıyor musun?</p>
      </Dialog>
    </>
  );
}

export const Basic: Story = { render: () => <Demo /> };
export const Small:  Story = { render: () => <Demo size="sm" /> };
export const Large:  Story = { render: () => <Demo size="lg" /> };

export const WithForm: Story = {
  render: () => {
    function FormDemo() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <Button onClick={() => setOpen(true)}>Proje oluştur</Button>
          <Dialog
            open={open}
            onOpenChange={setOpen}
            title="Yeni proje"
            footer={
              <>
                <Button variant="ghost" onClick={() => setOpen(false)}>İptal</Button>
                <Button onClick={() => setOpen(false)}>Oluştur</Button>
              </>
            }
          >
            <div className="space-y-3">
              <div>
                <Label htmlFor="name" required>İsim</Label>
                <Input id="name" placeholder="Müşteri portalı" className="mt-1" />
              </div>
              <div>
                <Label htmlFor="desc">Açıklama</Label>
                <Input id="desc" placeholder="Opsiyonel" className="mt-1" />
              </div>
            </div>
          </Dialog>
        </>
      );
    }
    return <FormDemo />;
  },
};
