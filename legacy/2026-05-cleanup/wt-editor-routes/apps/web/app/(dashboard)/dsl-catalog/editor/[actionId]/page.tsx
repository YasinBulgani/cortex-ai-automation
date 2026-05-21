"use client";

import { useParams } from "next/navigation";

import { DslActionEditor } from "@/components/dsl/DslActionEditor";

export default function EditDslActionPage() {
  const params = useParams<{ actionId?: string }>();
  const actionId = Array.isArray(params?.actionId)
    ? params.actionId[0]
    : params?.actionId;

  if (!actionId) {
    return (
      <div className="p-6 text-slate-400">Cümlecik ID'si belirtilmedi.</div>
    );
  }

  return <DslActionEditor mode="edit" actionId={actionId} />;
}
