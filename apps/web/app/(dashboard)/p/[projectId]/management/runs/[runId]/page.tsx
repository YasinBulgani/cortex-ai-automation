import { redirect } from "next/navigation";

export default function RunDetailPage({
  params,
}: {
  params: { projectId: string; runId: string };
}) {
  redirect(`/p/${params.projectId}/management/runs/${params.runId}/execute`);
}
