import { Check, ChevronDown, Sparkles, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MODELS, type ModelId } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ModelSelector({
  value,
  onChange,
  className,
  compact = false,
}: {
  value: ModelId;
  onChange: (model: ModelId) => void;
  className?: string;
  compact?: boolean;
}) {
  const active = MODELS.find((model) => model.id === value) ?? MODELS[0]!;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "gap-1.5 rounded-xl px-2.5 text-muted-foreground hover:text-foreground",
            className,
          )}
        >
          {active.id === "auto" ? (
            <Sparkles className="size-3.5 text-brand" />
          ) : (
            <Zap className="size-3.5 text-brand" />
          )}
          <span className={cn("font-medium", compact && "sr-only sm:not-sr-only")}>
            {active.name}
          </span>
          <ChevronDown className="size-3.5 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64 rounded-2xl p-1.5">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
          Model
        </DropdownMenuLabel>
        {MODELS.map((model) => (
          <DropdownMenuItem
            key={model.id}
            onSelect={() => onChange(model.id)}
            className="flex items-start gap-2 rounded-xl px-2.5 py-2"
          >
            <span className="mt-0.5">
              {model.id === "auto" ? (
                <Sparkles className="size-4 text-brand" />
              ) : (
                <Zap className="size-4 text-brand" />
              )}
            </span>
            <span className="flex-1">
              <span className="block text-sm font-medium">{model.name}</span>
              <span className="block text-xs text-muted-foreground">{model.description}</span>
            </span>
            {model.id === value ? <Check className="mt-0.5 size-4 text-brand" /> : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
