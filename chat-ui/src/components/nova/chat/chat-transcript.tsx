import {
  Conversation as ConversationScroller,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { MessageItem } from "@/components/nova/message-item";
import type { ChatMessage } from "@/lib/types";

export interface ChatTranscriptProps {
  messages: ChatMessage[];
  streamingMessageId: string | null;
  showTimestamps: boolean;
  compact: boolean;
  userInitials: string;
  onRegenerate: () => void;
  onFeedback: (messageId: string, value: "up" | "down") => void;
}

export function ChatTranscript({
  messages,
  streamingMessageId,
  showTimestamps,
  compact,
  userInitials,
  onRegenerate,
  onFeedback,
}: ChatTranscriptProps) {
  const lastAssistantId = [...messages].reverse().find((item) => item.role === "assistant")?.id;

  return (
    <ConversationScroller className="min-h-0 flex-1">
      <ConversationContent className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
        {messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            isStreaming={message.id === streamingMessageId}
            isLastAssistant={message.id === lastAssistantId}
            showTimestamp={showTimestamps}
            compact={compact}
            userInitials={userInitials}
            onRegenerate={onRegenerate}
            onFeedback={(value) => onFeedback(message.id, value)}
          />
        ))}
      </ConversationContent>
      <ConversationScrollButton />
    </ConversationScroller>
  );
}
