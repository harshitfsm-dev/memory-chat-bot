import {
  Archive,
  ChevronDown,
  MoreHorizontal,
  PanelLeft,
  Pencil,
  Share2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { ModelSelector } from "@/components/nova/model-selector";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Conversation, ModelId } from "@/lib/types";

export interface ChatHeaderProps {
  conversation: Conversation | null;
  onToggleSidebar: () => void;
  onRename: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onModelChange: (model: ModelId) => void;
  model: ModelId;
}

export function ChatHeader({
  conversation,
  onToggleSidebar,
  onRename,
  onDelete,
  onArchive,
  onModelChange,
  model,
}: ChatHeaderProps) {
  const title = conversation?.title ?? "New chat";

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-1 border-b bg-background/85 px-2.5 backdrop-blur-md sm:px-4">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Toggle sidebar"
        onClick={onToggleSidebar}
        className="rounded-xl"
      >
        <PanelLeft className="size-4" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="min-w-0 gap-1.5 rounded-xl px-2 font-semibold">
            <span className="max-w-[42vw] truncate sm:max-w-sm">{title}</span>
            <ChevronDown className="size-4 shrink-0 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56 rounded-2xl">
          <DropdownMenuItem className="rounded-xl" onSelect={onRename} disabled={!conversation}>
            <Pencil className="size-4" /> Rename
          </DropdownMenuItem>
          <DropdownMenuItem className="rounded-xl" onSelect={onArchive} disabled={!conversation}>
            <Archive className="size-4" />
            {conversation?.archived ? "Unarchive" : "Archive"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="rounded-xl text-destructive focus:text-destructive"
            onSelect={onDelete}
            disabled={!conversation}
          >
            <Trash2 className="size-4" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <div className="ml-auto flex items-center gap-1">
        <div className="hidden sm:block">
          <ModelSelector value={model} onChange={onModelChange} />
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="hidden gap-1.5 rounded-xl text-muted-foreground hover:text-foreground sm:flex"
          onClick={() => toast.success("Share link copied", { description: "Anyone with the link can view this chat." })}
        >
          <Share2 className="size-4" /> Share
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="More options" className="rounded-xl">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 rounded-2xl">
            <DropdownMenuItem
              className="rounded-xl sm:hidden"
              onSelect={() => toast.success("Share link copied")}
            >
              <Share2 className="size-4" /> Share
            </DropdownMenuItem>
            <DropdownMenuItem
              className="rounded-xl"
              onSelect={() => toast.info("Export is simulated in this preview")}
            >
              <Archive className="size-4" /> Export transcript
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
