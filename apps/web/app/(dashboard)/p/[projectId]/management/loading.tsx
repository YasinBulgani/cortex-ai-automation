import { PageHeaderSkeleton, TableSkeleton, SectionSkeleton } from "@/components/ui/skeleton";

export default function ManagementLoading() {
  return (
    <div className="space-y-6 p-6" data-testid="management-loading">
      <PageHeaderSkeleton />
      <SectionSkeleton />
      <TableSkeleton rows={6} />
    </div>
  );
}
