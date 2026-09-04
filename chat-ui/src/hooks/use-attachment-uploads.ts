import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { MAX_UPLOAD_SIZE, uploadAttachment } from "@/api";
import type { UploadHandle } from "@/api/types";
import { formatBytes } from "@/lib/files";
import type { Attachment } from "@/lib/types";

/** Owns attachment upload state; all transport lives in the files endpoint. */
export function useAttachmentUploads() {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const uploads = useRef<UploadHandle[]>([]);

  useEffect(() => () => uploads.current.forEach((upload) => upload.cancel()), []);

  const addFiles = useCallback((files: File[]) => {
    for (const file of files) {
      if (file.size > MAX_UPLOAD_SIZE) {
        toast.error(`${file.name} is larger than ${formatBytes(MAX_UPLOAD_SIZE)}`);
        continue;
      }
      const upload = uploadAttachment(file, (next) => {
        setAttachments((prev) => prev.map((item) => (item.id === next.id ? next : item)));
      });
      uploads.current.push(upload);
      setAttachments((prev) => [...prev, upload.attachment]);
    }
  }, []);

  const removeAttachment = useCallback((id: string) => {
    const upload = uploads.current.find((item) => item.attachment.id === id);
    upload?.cancel();
    uploads.current = uploads.current.filter((item) => item.attachment.id !== id);
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearAttachments = useCallback(() => {
    uploads.current.forEach((upload) => upload.cancel());
    uploads.current = [];
    setAttachments([]);
  }, []);

  return { attachments, addFiles, removeAttachment, clearAttachments };
}
