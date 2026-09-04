import { createId } from "@/lib/id";
import type { Attachment } from "@/lib/types";
import type { UploadHandle } from "@/api/types";

export const MAX_UPLOAD_SIZE = 20 * 1024 * 1024;

function toAttachment(file: File): Attachment {
  return {
    id: createId(),
    name: file.name,
    mime: file.type || "application/octet-stream",
    size: file.size,
    status: "uploading",
    progress: 6,
    ...(file.type.startsWith("image/") ? { previewUrl: URL.createObjectURL(file) } : {}),
  };
}

/**
 * POST /files (multipart, with progress)
 *
 * Returns immediately with the pending attachment plus a promise that resolves
 * when the upload completes. Real implementation: XHR/fetch upload reporting
 * progress through the same `onProgress` callback.
 */
export function uploadAttachment(
  file: File,
  onProgress?: (attachment: Attachment) => void,
): UploadHandle {
  const attachment = toAttachment(file);
  let cancelled = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const done = new Promise<Attachment>((resolve) => {
    let progress = attachment.progress;
    const tick = () => {
      if (cancelled) return;
      progress = Math.min(100, progress + 12 + Math.random() * 22);
      const complete = progress >= 100;
      const next: Attachment = {
        ...attachment,
        progress: Math.round(progress),
        status: complete ? "done" : "uploading",
      };
      onProgress?.(next);
      if (complete) resolve(next);
      else timer = setTimeout(tick, 180 + Math.random() * 160);
    };
    timer = setTimeout(tick, 220);
  });

  return {
    attachment,
    cancel: () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    },
    done,
  };
}
