import { LoaderCircle, RotateCw, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  ApiError,
  forgetMemory,
  listMemories,
  type MemoryItemResponse,
  type UserMemoriesResponse,
} from "@/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "We couldn't update memory. Try again.";
}

function formatFactKey(key: string | null): string | null {
  if (!key) return null;
  const words = key.split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

interface MemoryGroupProps {
  title: string;
  description: string;
  emptyText: string;
  items: MemoryItemResponse[];
  pendingId: string | null;
  onForget: (memory: MemoryItemResponse) => void;
}

function MemoryGroup({
  title,
  description,
  emptyText,
  items,
  pendingId,
  onForget,
}: MemoryGroupProps) {
  return (
    <section aria-labelledby={`memory-${title.toLowerCase()}`}>
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <h3 id={`memory-${title.toLowerCase()}`} className="text-sm font-semibold">
            {title}
          </h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <Badge variant="outline" aria-label={`${items.length} ${title.toLowerCase()}`}>
          {items.length}
        </Badge>
      </div>

      {items.length === 0 ? (
        <p className="rounded-xl border border-dashed px-3 py-4 text-sm text-muted-foreground">
          {emptyText}
        </p>
      ) : (
        <ul className="divide-y rounded-xl border" aria-label={title}>
          {items.map((memory) => {
            const factLabel = formatFactKey(memory.memory_key);
            return (
              <li key={memory.id} className="flex items-start gap-3 px-3 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-5">{memory.content}</p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    {factLabel ? <Badge variant="secondary">{factLabel}</Badge> : null}
                    <time dateTime={memory.updated_at}>
                      Updated {formatDate(memory.updated_at)}
                    </time>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  aria-label={`Forget memory: ${memory.content}`}
                  disabled={pendingId !== null}
                  onClick={() => onForget(memory)}
                >
                  <Trash2 />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function MemoryLoadingState() {
  return (
    <div className="space-y-5" aria-label="Loading memories">
      {[0, 1].map((group) => (
        <div key={group} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      ))}
    </div>
  );
}

export function MemorySettingsPanel() {
  const [memories, setMemories] = useState<UserMemoriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [selectedMemory, setSelectedMemory] = useState<MemoryItemResponse | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const listRequestSeq = useRef(0);
  const committedMutationSeq = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const requestSeq = ++listRequestSeq.current;
    const mutationSeqAtStart = committedMutationSeq.current;
    setLoading(true);
    setLoadError(null);

    void listMemories()
      .then((result) => {
        if (
          !cancelled &&
          requestSeq === listRequestSeq.current &&
          mutationSeqAtStart === committedMutationSeq.current
        ) {
          setMemories(result);
        }
      })
      .catch((error: unknown) => {
        if (
          !cancelled &&
          requestSeq === listRequestSeq.current &&
          mutationSeqAtStart === committedMutationSeq.current
        ) {
          setLoadError(errorMessage(error));
        }
      })
      .finally(() => {
        if (!cancelled && requestSeq === listRequestSeq.current) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadVersion]);

  const openForgetDialog = (memory: MemoryItemResponse) => {
    setActionError(null);
    setSelectedMemory(memory);
  };

  const handleForget = async () => {
    if (!selectedMemory || pendingId) return;

    const memory = selectedMemory;
    setPendingId(memory.id);
    setActionError(null);
    try {
      await forgetMemory(memory.id, memory.updated_at);
      committedMutationSeq.current += 1;
      setMemories((current) =>
        current
          ? {
              facts: current.facts.filter((item) => item.id !== memory.id),
              episodes: current.episodes.filter((item) => item.id !== memory.id),
            }
          : current,
      );
      setSelectedMemory(null);
      toast.success("Memory forgotten");
    } catch (error) {
      const message = errorMessage(error);
      if (error instanceof ApiError && error.status === 404) {
        committedMutationSeq.current += 1;
        setMemories((current) =>
          current
            ? {
                facts: current.facts.filter((item) => item.id !== memory.id),
                episodes: current.episodes.filter((item) => item.id !== memory.id),
              }
            : current,
        );
        setSelectedMemory(null);
        setReloadVersion((version) => version + 1);
        toast.error("That memory is no longer available. Refreshing the list.");
      } else if (error instanceof ApiError && error.status === 409) {
        setSelectedMemory(null);
        setReloadVersion((version) => version + 1);
        toast.error("That memory changed. Review the updated memory before forgetting it.");
      } else {
        setActionError(message);
        toast.error(message);
      }
    } finally {
      setPendingId(null);
    }
  };

  const total = memories ? memories.facts.length + memories.episodes.length : 0;

  return (
    <div className="space-y-5 py-3" aria-busy={loading}>
      <div>
        <h2 className="text-base font-semibold">Long-term memory</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Review facts and past decisions Nova may use in future responses.
        </p>
      </div>

      {loading && !memories ? <MemoryLoadingState /> : null}

      {loadError && !memories ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4" role="alert">
          <p className="text-sm">{loadError}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-3 rounded-xl"
            onClick={() => setReloadVersion((version) => version + 1)}
          >
            <RotateCw /> Retry
          </Button>
        </div>
      ) : null}

      {loadError && memories ? (
        <div
          className="flex items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2"
          role="alert"
        >
          <p className="text-sm">{loadError}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="shrink-0 rounded-xl"
            onClick={() => setReloadVersion((version) => version + 1)}
          >
            <RotateCw /> Retry
          </Button>
        </div>
      ) : null}

      {memories && total === 0 ? (
        <div className="rounded-xl border border-dashed px-4 py-8 text-center">
          <p className="text-sm font-medium">No saved memories</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Durable preferences and technical decisions will appear here.
          </p>
        </div>
      ) : null}

      {memories && total > 0 ? (
        <div className="space-y-6" aria-live="polite">
          <MemoryGroup
            title="Facts"
            description="Pinned preferences and ongoing technical context."
            emptyText="No pinned facts are saved."
            items={memories.facts}
            pendingId={pendingId}
            onForget={openForgetDialog}
          />
          <MemoryGroup
            title="Episodes"
            description="Past technical decisions and milestones."
            emptyText="No past episodes are saved."
            items={memories.episodes}
            pendingId={pendingId}
            onForget={openForgetDialog}
          />
        </div>
      ) : null}

      {loading && memories ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground" role="status">
          <LoaderCircle className="animate-spin" /> Refreshing memories
        </p>
      ) : null}

      <AlertDialog
        open={selectedMemory !== null}
        onOpenChange={(open) => {
          if (!open && !pendingId) {
            setSelectedMemory(null);
            setActionError(null);
          }
        }}
      >
        <AlertDialogContent className="rounded-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle>Forget this memory?</AlertDialogTitle>
            <AlertDialogDescription>
              Nova will stop using this memory in future chats.
              {selectedMemory ? (
                <span className="mt-3 block rounded-xl bg-muted px-3 py-2 text-sm text-foreground">
                  {selectedMemory.content}
                </span>
              ) : null}
            </AlertDialogDescription>
            {actionError ? (
              <p className="text-sm text-destructive" role="alert">
                {actionError}
              </p>
            ) : null}
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-xl" disabled={pendingId !== null}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={pendingId !== null}
              onClick={(event) => {
                event.preventDefault();
                void handleForget();
              }}
            >
              {pendingId ? <LoaderCircle className="animate-spin" /> : <Trash2 />}
              {pendingId ? "Forgetting" : "Forget memory"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
