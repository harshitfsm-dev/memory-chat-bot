import { Mic, Paperclip, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { AttachmentGrid } from "@/components/nova/file-attachment";
import { ModelSelector } from "@/components/nova/model-selector";
import { Button } from "@/components/ui/button";
import type { Attachment, ModelId } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface ChatComposerProps {
  value: string;
  onValueChange: (value: string) => void;
  attachments: Attachment[];
  onAddFiles: (files: File[]) => void;
  onRemoveAttachment: (id: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  isStreaming: boolean;
  model: ModelId;
  onModelChange: (model: ModelId) => void;
  enterToSend: boolean;
  autoFocusKey?: string;
}

export function ChatComposer({
  value,
  onValueChange,
  attachments,
  onAddFiles,
  onRemoveAttachment,
  onSubmit,
  onStop,
  isStreaming,
  model,
  onModelChange,
  enterToSend,
  autoFocusKey,
}: ChatComposerProps) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [listening, setListening] = useState(false);

  const uploading = attachments.some((attachment) => attachment.status === "uploading");
  const canSend = (value.trim().length > 0 || attachments.length > 0) && !uploading && !isStreaming;

  useEffect(() => {
    textareaRef.current?.focus();
  }, [autoFocusKey]);

  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus();
  }, [isStreaming]);

  return (
    <div className="mx-auto w-full max-w-3xl">
      {isStreaming ? (
        <div className="mb-2 flex justify-center">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onStop}
            className="gap-1.5 rounded-full bg-card shadow-soft"
          >
            <Square className="size-3 fill-current" /> Stop generating
          </Button>
        </div>
      ) : null}

      <PromptInput
        className="rounded-3xl border-input bg-card shadow-soft transition-shadow focus-within:shadow-lifted"
        onSubmit={(_message, event) => {
          event.preventDefault();
          if (canSend) onSubmit();
        }}
      >
        {attachments.length > 0 ? (
          <div className="px-3 pt-3">
            <AttachmentGrid attachments={attachments} onRemove={onRemoveAttachment} />
          </div>
        ) : null}

        <PromptInputTextarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !enterToSend) {
              // "Enter to send" disabled: newline instead of submitting
              event.stopPropagation();
              return;
            }
            if (event.key === "Enter" && !event.shiftKey && enterToSend && !canSend) {
              event.preventDefault();
            }
          }}
          placeholder="Message Nova…"
          className="max-h-56 min-h-[52px] px-4 text-[15px] placeholder:text-muted-foreground/70"
        />

        <PromptInputFooter className="gap-1 border-0 px-2.5 pb-2.5">
          <PromptInputTools className="gap-0.5">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Attach files"
              onClick={() => fileRef.current?.click()}
              className="rounded-xl text-muted-foreground hover:text-foreground"
            >
              <Paperclip className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Dictate message"
              onClick={() => {
                setListening((prev) => !prev);
                toast.info(listening ? "Stopped listening" : "Voice input is simulated for now");
              }}
              className={cn(
                "rounded-xl text-muted-foreground hover:text-foreground",
                listening && "bg-brand-soft text-brand",
              )}
            >
              <Mic className="size-4" />
            </Button>
            <ModelSelector value={model} onChange={onModelChange} compact />
          </PromptInputTools>

          <div className="ml-auto flex items-center gap-2">
            <span className="hidden text-[11px] text-muted-foreground sm:block">
              {enterToSend ? "Enter to send · Shift + Enter for a new line" : "Shift + Enter to send"}
            </span>
            <PromptInputSubmit
              disabled={!canSend && !isStreaming}
              status={isStreaming ? "streaming" : "ready"}
              {...(isStreaming ? { onStop } : {})}
              className="rounded-full"
            />
          </div>
        </PromptInputFooter>
      </PromptInput>

      <input
        ref={fileRef}
        type="file"
        multiple
        className="hidden"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.md,image/*"
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length > 0) onAddFiles(files);
          event.target.value = "";
        }}
      />

      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        Nova can make mistakes. Responses in this preview are simulated.
      </p>
    </div>
  );
}
