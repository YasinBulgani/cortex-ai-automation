"use client";

import { useCallback, useEffect, useState } from "react";

export type ChecklistItemId =
  | "create_project"
  | "create_first_scenario"
  | "run_first_execution"
  | "view_execution_results"
  | "use_ai_assistant"
  | "create_api_test"
  | "schedule_recurring_run"
  | "explore_flaky_tests"
  | "export_report"
  | "invite_team_member";

export type ChecklistItem = {
  id: ChecklistItemId;
  title: string;
  description: string;
  href: string;
  icon: string;
  required: boolean;
};

export const CHECKLIST: ChecklistItem[] = [
  {
    id: "create_project",
    title: "İlk projeyi oluştur",
    description: "Çalışma alanını kur — proje, baseURL, ortam ayarları",
    href: "/onboarding",
    icon: "🏗️",
    required: true,
  },
  {
    id: "create_first_scenario",
    title: "İlk senaryonu yaz",
    description: "Manuel ya da AI (Sıfır Bilgi) ile başla",
    href: "/scenarios/new",
    icon: "✍️",
    required: true,
  },
  {
    id: "run_first_execution",
    title: "İlk testi koş",
    description: "Senaryonun çalıştığını gör — yeşil/kırmızı sonuçlar",
    href: "/executions/new",
    icon: "▶️",
    required: true,
  },
  {
    id: "view_execution_results",
    title: "Sonuçları incele",
    description: "Screenshot, video, step-by-step rapor",
    href: "/executions",
    icon: "🔍",
    required: false,
  },
  {
    id: "use_ai_assistant",
    title: "AI asistana sor",
    description: "Cmd+J — bağlama duyarlı yardım al",
    href: "/ai-chat",
    icon: "🤖",
    required: false,
  },
  {
    id: "create_api_test",
    title: "API testi ekle",
    description: "Postman/OpenAPI import veya manuel chain builder",
    href: "/api-tests",
    icon: "🔌",
    required: false,
  },
  {
    id: "schedule_recurring_run",
    title: "Periyodik koşum kur",
    description: "Cron ile her gün/saat smoke testlerini koş",
    href: "/schedules",
    icon: "⏰",
    required: false,
  },
  {
    id: "explore_flaky_tests",
    title: "Flaky testleri keşfet",
    description: "Hangi testler kararsız? Quarantine yap",
    href: "/flaky",
    icon: "🎲",
    required: false,
  },
  {
    id: "export_report",
    title: "Raporunu paylaş",
    description: "PDF/Excel/Markdown formatında dışa aktar",
    href: "/reports",
    icon: "📤",
    required: false,
  },
  {
    id: "invite_team_member",
    title: "Takım arkadaşı davet et",
    description: "Çoklu kullanıcı — RBAC ile rolleri ayarla",
    href: "/admin/users",
    icon: "👥",
    required: false,
  },
];

const STORAGE_KEY = "neurex_learning_checklist_v1";

function readCompleted(): Set<ChecklistItemId> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

function writeCompleted(items: Set<ChecklistItemId>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(items)));
  } catch {
    /* quota */
  }
}

export function useLearningChecklist() {
  const [completed, setCompleted] = useState<Set<ChecklistItemId>>(new Set());
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setCompleted(readCompleted());
    try {
      setDismissed(localStorage.getItem("neurex_checklist_dismissed") === "1");
    } catch {
      /* ignore */
    }
  }, []);

  const markComplete = useCallback((id: ChecklistItemId) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      next.add(id);
      writeCompleted(next);
      return next;
    });
  }, []);

  const markIncomplete = useCallback((id: ChecklistItemId) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      next.delete(id);
      writeCompleted(next);
      return next;
    });
  }, []);

  const dismiss = useCallback(() => {
    try {
      localStorage.setItem("neurex_checklist_dismissed", "1");
    } catch {
      /* ignore */
    }
    setDismissed(true);
  }, []);

  const totalRequired = CHECKLIST.filter((i) => i.required).length;
  const completedRequired = CHECKLIST.filter(
    (i) => i.required && completed.has(i.id),
  ).length;
  const totalCompleted = CHECKLIST.filter((i) => completed.has(i.id)).length;
  const progressPct = Math.round((totalCompleted / CHECKLIST.length) * 100);
  const requiredCompletedAll = completedRequired === totalRequired;

  return {
    items: CHECKLIST,
    completed,
    dismissed,
    markComplete,
    markIncomplete,
    dismiss,
    totalCompleted,
    totalItems: CHECKLIST.length,
    progressPct,
    requiredCompletedAll,
  };
}
