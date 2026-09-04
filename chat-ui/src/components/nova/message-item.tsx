import { Check, Copy, MoreHorizontal, Pencil, RefreshCw, Share2, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { AttachmentGrid } from "@/components/nova/file-attachment";
import { NovaMark } from "@/components/nova/brand";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime } from "@/lib/date-groups";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface MessageItemProps {
  message: ChatMessage;
  isStreaming: boolean;
  isLastAssistant: boolean;
  showTimestamp: boolean;
  compact: boolean;
  userInitials: string;
  onRegenerate: () => void;
  onFeedback: (value: "up" | "down") => void;
}

export function MessageItem({
  message,
  isStreaming,
  isLastAssistant,
  showTimestamp,
  compact,
  userInitials,
  onRegenerate,
  onFeedback,
}: MessageItemProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast.success("Copied to clipboard");
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      toast.error("Couldn't copy this message");
    }
  };

  return (
    <Message from={message.role} className={cn("max-w-full", compact ? "gap-1" : "gap-2")}>
      <div className={cn("flex w-full gap-3", isUser && "flex-row-reverse")}>
        {isUser ? (
          <Avatar className="mt-0.5 hidden size-8 shrink-0 sm:flex">
            <AvatarFallback className="bg-surface-strong text-[11px] font-semibold">
              {userInitials}
            </AvatarFallback>
          </Avatar>
        ) : (
          <NovaMark className="mt-0.5 hidden sm:grid" />
        )}

        <div className={cn("flex min-w-0 flex-1 flex-col gap-2", isUser && "items-end")}>
          {message.attachments?.length ? (
            <AttachmentGrid
              attachments={message.attachments}
              className={cn(isUser && "justify-end")}
            />
          ) : null}

          {isStreaming && message.content.length === 0 ? (
            <Shimmer className="text-sm">Thinking…</Shimmer>
          ) : (
            <MessageContent
              className={cn(
                "group-[.is-user]:bg-user-bubble group-[.is-user]:text-user-bubble-foreground group-[.is-user]:rounded-2xl group-[.is-user]:rounded-tr-md",
                "group-[.is-assistant]:prose-sm",
                compact ? "text-[13.5px]" : "text-[15px]",
              )}
            >
              {isUser ? (
                <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
              ) : (
                <>
                  <MessageResponse isAnimating={isStreaming}>{message.content}</MessageResponse>
                  {isStreaming ? <span className="nova-caret">▍</span> : null}
                </>
              )}
            </MessageContent>
          )}

          <div
            className={cn(
              "flex items-center gap-1 text-[11px] text-muted-foreground",
              isUser && "flex-row-reverse",
            )}
          >
            {showTimestamp ? (
              <span className={cn(isUser ? "pl-1" : "pr-1")}>
                {formatDateTime(message.createdAt)}
              </span>
            ) : null}

            {!isStreaming ? (
              <MessageActions
                className={cn(
                  "opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100",
                  isLastAssistant && "opacity-100",
                )}
              >
                <MessageAction tooltip="Copy" onClick={copy} className="rounded-lg">
                  {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                </MessageAction>

                {isUser ? null : (
                  <>
                    <MessageAction
                      tooltip="Regenerate"
                      onClick={onRegenerate}
                      className="rounded-lg"
                    >
                      <RefreshCw className="size-3.5" />
                    </MessageAction>
                    <MessageAction
                      tooltip="Good response"
                      onClick={() => onFeedback("up")}
                      className={cn("rounded-lg", message.feedback === "up" && "text-brand")}
                    >
                      <ThumbsUp className="size-3.5" />
                    </MessageAction>
                    <MessageAction
                      tooltip="Bad response"
                      onClick={() => onFeedback("down")}
                      className={cn(
                        "rounded-lg",
                        message.feedback === "down" && "text-destructive",
                      )}
                    >
                      <ThumbsDown className="size-3.5" />
                    </MessageAction>
                  </>
                )}

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <MessageAction tooltip="More" className="rounded-lg">
                      <MoreHorizontal className="size-3.5" />
                    </MessageAction>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align={isUser ? "end" : "start"} className="rounded-2xl">
                    <DropdownMenuItem
                      className="rounded-xl"
                      onSelect={() => toast.info("Sharing a single message is coming soon")}
                    >
                      <Share2 className="size-4" /> Share message
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="rounded-xl"
                      onSelect={() => toast.info("Inline editing is coming soon")}
                    >
                      <Pencil className="size-4" /> Edit in composer
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </MessageActions>
            ) : null}
          </div>
        </div>
      </div>
    </Message>
  );
}
