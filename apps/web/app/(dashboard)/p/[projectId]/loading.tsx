import { PageHeaderSkeleton, TableSkeleton } from "@/components/ui/skeleton";

export default function ProjectSectionLoading() {
  return (
    <div className="space-y-6 p-6" data-testid="project-loading">
      <PageHeaderSkeleton />
      <TableSkeleton />
    </div>
  );
}
