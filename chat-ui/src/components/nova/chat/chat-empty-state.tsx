import { NovaMark } from "@/components/nova/brand";
import { SuggestionCards } from "@/components/nova/suggestion-cards";

export interface ChatEmptyStateProps {
  userName: string;
  onSelectPrompt: (prompt: string) => void;
}

export function ChatEmptyState({ userName, onSelectPrompt }: ChatEmptyStateProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4">
      <div className="w-full max-w-3xl text-center">
        <NovaMark className="mx-auto size-11" />
        <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
          {`Hi ${userName.split(" ")[0]}, what can I help with?`}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Ask anything, drop in a file, or start from a suggestion.
        </p>
        <SuggestionCards className="mt-7 text-left" onSelect={onSelectPrompt} />
      </div>
    </div>
  );
}
