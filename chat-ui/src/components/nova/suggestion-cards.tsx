import {
  BarChart3,
  CalendarCheck,
  FileText,
  GraduationCap,
  Lightbulb,
  PenLine,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface Suggestion {
  icon: LucideIcon;
  title: string;
  hint: string;
  prompt: string;
}

export const SUGGESTIONS: Suggestion[] = [
  {
    icon: FileText,
    title: "Summarize a document",
    hint: "Pull out decisions and owners",
    prompt: "Summarize this document into key decisions, owners and open questions.",
  },
  {
    icon: PenLine,
    title: "Write something",
    hint: "Draft in my voice",
    prompt: "Write a short launch announcement for a new AI summarization feature.",
  },
  {
    icon: BarChart3,
    title: "Analyze data",
    hint: "Find what changed",
    prompt: "Analyze this month's sales numbers and tell me the three things that changed most.",
  },
  {
    icon: Lightbulb,
    title: "Brainstorm ideas",
    hint: "Ten angles, no filler",
    prompt: "Brainstorm ten non-obvious ideas for growing word-of-mouth referrals.",
  },
  {
    icon: GraduationCap,
    title: "Explain a concept",
    hint: "At the right depth",
    prompt: "Explain vector embeddings to me as if I know basic linear algebra.",
  },
  {
    icon: CalendarCheck,
    title: "Help me plan something",
    hint: "Turn goals into steps",
    prompt: "Help me plan a two-week product launch, working backwards from launch day.",
  },
];

export function SuggestionCards({
  onSelect,
  className,
}: {
  onSelect: (prompt: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("grid w-full gap-2.5 sm:grid-cols-2 lg:grid-cols-3", className)}>
      {SUGGESTIONS.map(({ icon: Icon, title, hint, prompt }) => (
        <button
          key={title}
          type="button"
          onClick={() => onSelect(prompt)}
          className="group flex items-start gap-3 rounded-2xl border bg-card p-3.5 text-left transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-soft focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-surface-strong text-brand transition-colors group-hover:bg-brand-soft">
            <Icon className="size-4" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[13.5px] font-medium">{title}</span>
            <span className="block truncate text-xs text-muted-foreground">{hint}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
