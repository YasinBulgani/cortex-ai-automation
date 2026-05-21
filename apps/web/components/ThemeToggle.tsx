"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("tspm_theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = stored === "dark" || (!stored && prefersDark);
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("tspm_theme", next ? "dark" : "light");
  }

  return (
    <Button type="button" variant="ghost" onClick={toggle} aria-label="Tema" data-testid="header-btn-theme">
      {dark ? "Açık" : "Koyu"}
    </Button>
  );
}
