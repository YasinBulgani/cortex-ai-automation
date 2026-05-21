import type { Meta, StoryObj } from "@storybook/react";
import { useEffect, useState } from "react";
import { CommandPalette, type CommandItem } from "./command-palette";
import { Button } from "../primitives/button";

const meta: Meta<typeof CommandPalette> = {
  title: "Patterns/CommandPalette",
  component: CommandPalette,
  tags: ["autodocs"],
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof CommandPalette>;

function Demo() {
  const [open, setOpen] = useState(false);

  // ⌘K / Ctrl+K kısayolu
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(o => !o);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const items: CommandItem[] = [
    { id: "g1", label: "Yeni proje",   group: "Eylemler", shortcut: "⌘N", onSelect: () => alert("Yeni proje") },
    { id: "g2", label: "Yeni senaryo", group: "Eylemler", shortcut: "⌘⇧N", keywords: ["test", "case"], onSelect: () => alert("Yeni senaryo") },
    { id: "g3", label: "Yeni koşum",   group: "Eylemler", onSelect: () => alert("Yeni koşum") },

    { id: "n1", label: "Projeler",     group: "Navigasyon", onSelect: () => alert("Projeler") },
    { id: "n2", label: "Ayarlar",      group: "Navigasyon", onSelect: () => alert("Ayarlar") },
    { id: "n3", label: "Faturalama",   group: "Navigasyon", keywords: ["abonelik", "ödeme"], onSelect: () => alert("Faturalama") },

    { id: "t1", label: "Tema: aydınlık", group: "Tema", onSelect: () => {} },
    { id: "t2", label: "Tema: karanlık", group: "Tema", onSelect: () => {} },
    { id: "t3", label: "Tema: sistem",   group: "Tema", onSelect: () => {} },

    { id: "d1", label: "Hesabı sil", group: "Tehlikeli", danger: true, onSelect: () => alert("Sil") },
  ];

  return (
    <div className="p-8 space-y-3">
      <Button onClick={() => setOpen(true)}>Komut paletini aç (⌘K)</Button>
      <p className="text-sm text-fg-muted">
        Paletteyi her yerden açmak için ⌘K / Ctrl+K kullan. ↑↓ ile gez, Enter ile seç, ESC kapatır.
      </p>
      <CommandPalette open={open} onOpenChange={setOpen} items={items} />
    </div>
  );
}

export const Default: Story = { render: () => <Demo /> };
