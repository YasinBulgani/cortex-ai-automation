import { redirect } from "next/navigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Neurex QA — Giriş",
  description: "Neurex QA güvenli çalışma alanına giriş yapın.",
};

export default function HomePage() {
  redirect("/login");
}
