import { Skeleton } from "@/components/ui/skeleton";

/** Shown while a thread's transcript is being fetched from the backend. */
export function ChatTranscriptSkeleton() {
  return (
    <div className="min-h-0 flex-1 overflow-hidden">
      <div className="mx-auto w-full max-w-3xl space-y-6 px-3 py-6 sm:px-4">
        {Array.from({ length: 4 }).map((_, index) => {
          const fromUser = index % 2 === 0;
          return (
            <div key={index} className={fromUser ? "flex justify-end" : "flex justify-start gap-3"}>
              {!fromUser ? <Skeleton className="size-8 shrink-0 rounded-full" /> : null}
              <div className={fromUser ? "w-2/3 space-y-2" : "w-3/4 space-y-2"}>
                <Skeleton className="h-4 w-full rounded-lg" />
                <Skeleton className={fromUser ? "h-4 w-1/2 rounded-lg" : "h-4 w-5/6 rounded-lg"} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
