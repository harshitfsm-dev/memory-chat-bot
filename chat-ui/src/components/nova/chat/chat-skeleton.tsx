import { Skeleton } from "@/components/ui/skeleton";

/** Shown while the API layer hydrates session, settings and conversations. */
export function ChatSkeleton() {
  return (
    <div className="flex min-h-screen">
      <div className="hidden w-72 border-r bg-sidebar p-3 md:block">
        <Skeleton className="h-9 w-full rounded-xl" />
        <Skeleton className="mt-3 h-9 w-full rounded-xl" />
        <div className="mt-6 space-y-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full rounded-xl" />
          ))}
        </div>
      </div>
      <div className="flex-1 p-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="mt-6 h-32 w-full max-w-2xl rounded-2xl" />
      </div>
    </div>
  );
}
