import type { Meta, StoryObj } from "@storybook/react";
import { ToastProvider, useToast } from "./toast";
import { Button } from "./button";

const meta: Meta<typeof ToastProvider> = {
  title: "Primitives/Toast",
  component: ToastProvider,
  tags: ["autodocs"],
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof ToastProvider>;

function Demo() {
  const { toast, success, error, warning, info, dismissAll } = useToast();
  return (
    <div className="p-6 flex flex-wrap gap-3">
      <Button onClick={() => info("Bilgilendirme mesajı")}>Info</Button>
      <Button onClick={() => success("İşlem tamamlandı")} variant="primary">Success</Button>
      <Button onClick={() => warning("Dikkat — bağlantı yavaş")} variant="subtle">Warning</Button>
      <Button onClick={() => error("Bir şeyler ters gitti")} variant="danger">Error</Button>
      <Button
        variant="outline"
        onClick={() =>
          toast({
            message: "Aksiyonlu toast",
            variant: "info",
            duration_ms: 0,
            action: { label: "Geri Al", onClick: () => alert("undo!") },
          })
        }
      >
        Action toast
      </Button>
      <Button variant="ghost" onClick={dismissAll}>Hepsini kapat</Button>
    </div>
  );
}

export const BottomRight: Story = {
  render: () => (
    <ToastProvider position="bottom-right">
      <Demo />
    </ToastProvider>
  ),
};

export const TopCenter: Story = {
  render: () => (
    <ToastProvider position="top-center">
      <Demo />
    </ToastProvider>
  ),
};

export const MaxLimit: Story = {
  name: "max=3 (older drops)",
  render: () => (
    <ToastProvider max={3}>
      <Demo />
    </ToastProvider>
  ),
};
