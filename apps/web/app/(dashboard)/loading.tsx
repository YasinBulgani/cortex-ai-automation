import { StatCardsSkeleton, SectionSkeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="space-y-6 p-6" data-testid="dashboard-loading">
      <div className="h-8 w-52 rounded bg-border/50 animate-pulse" />
      <StatCardsSkeleton />
      <SectionSkeleton />
    </div>
  );
}
