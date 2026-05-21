import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded bg-border/50", className)}
      {...props}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border border-slate-800 p-4 shadow-2xl">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-8 w-16" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-lg border border-slate-800">
      <div className="border-b border-slate-800 px-5 py-4">
        <Skeleton className="h-4 w-40" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 border-b border-slate-800 px-5 py-3 last:border-0">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-12" />
        </div>
      ))}
    </div>
  );
}

export function StatCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function SectionSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-lg border border-slate-800 p-5">
      <Skeleton className="h-5 w-40" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-full" />
        ))}
      </div>
    </div>
  );
}

export function PageHeaderSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-7 w-64" />
      <Skeleton className="h-4 w-96 max-w-full" />
    </div>
  );
}
