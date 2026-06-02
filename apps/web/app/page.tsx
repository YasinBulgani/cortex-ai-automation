import { redirect } from "next/navigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Neurex QA",
  description: "Neurex QA operasyon paneli.",
};

export default function HomePage() {
  redirect("/projects");
}
