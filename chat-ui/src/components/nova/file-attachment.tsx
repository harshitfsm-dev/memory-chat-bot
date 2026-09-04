import { AlertCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { fileIcon, fileKindLabel, formatBytes } from "@/lib/files";
import type { Attachment } from "@/lib/types";
import { cn } from "@/lib/utils";

export function FileAttachment({
  attachment,
  onRemove,
  className,
}: {
  attachment: Attachment;
  onRemove?: (id: string) => void;
  className?: string;
}) {
  const Icon = fileIcon(attachment.mime, attachment.name);
  const isImage = attachment.mime.startsWith("image/") && attachment.previewUrl;

  return (
    <div
      className={cn(
        "group/att relative flex w-full min-w-0 items-center gap-2.5 rounded-xl border bg-card p-2 pr-8 text-left shadow-sm sm:w-64",
        attachment.status === "error" && "border-destructive/40",
        className,
      )}
    >
      {isImage ? (
        <img
          src={attachment.previewUrl}
          alt={attachment.name}
          className="size-9 shrink-0 rounded-lg object-cover"
        />
      ) : (
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-strong">
          {attachment.status === "error" ? (
            <AlertCircle className="size-4 text-destructive" />
          ) : (
            <Icon className="size-4 text-brand" />
          )}
        </span>
      )}

      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-medium">{attachment.name}</span>
        <span className="block truncate text-[11px] text-muted-foreground">
          {attachment.status === "uploading"
            ? `Uploading · ${Math.round(attachment.progress)}%`
            : attachment.status === "error"
              ? "Upload failed"
              : `${fileKindLabel(attachment.mime, attachment.name)} · ${formatBytes(attachment.size)}`}
        </span>
        {attachment.status === "uploading" ? (
          <Progress value={attachment.progress} className="mt-1.5 h-1" />
        ) : null}
      </span>

      {onRemove ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label={`Remove ${attachment.name}`}
          onClick={() => onRemove(attachment.id)}
          className="absolute top-1.5 right-1.5 rounded-lg text-muted-foreground hover:text-foreground"
        >
          <X className="size-3.5" />
        </Button>
      ) : null}
    </div>
  );
}

export function AttachmentGrid({
  attachments,
  onRemove,
  className,
}: {
  attachments: Attachment[];
  onRemove?: (id: string) => void;
  className?: string;
}) {
  if (attachments.length === 0) return null;
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {attachments.map((attachment) => (
        <FileAttachment
          key={attachment.id}
          attachment={attachment}
          {...(onRemove ? { onRemove } : {})}
        />
      ))}
    </div>
  );
}
