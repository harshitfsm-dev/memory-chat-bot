import { Link } from "@tanstack/react-router";
import { Archive, MessageSquare, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { groupConversations } from "@/lib/date-groups";
import type { Conversation } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface ChatListProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: () => void;
  onRename: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  emptyLabel: string;
}

export function ChatList({
  conversations,
  activeId,
  onSelect,
  onRename,
  onDelete,
  onArchive,
  emptyLabel,
}: ChatListProps) {
  const groups = groupConversations(conversations);

  if (groups.length === 0) {
    return (
      <p className="px-3 py-6 text-center text-xs text-muted-foreground">{emptyLabel}</p>
    );
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <section key={group.label}>
          <h3 className="px-3 pb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            {group.label}
          </h3>
          <ul className="space-y-0.5">
            {group.items.map((conversation) => {
              const isActive = conversation.id === activeId;
              return (
                <li key={conversation.id} className="group/item relative">
                  <Link
                    to="/c/$chatId"
                    params={{ chatId: conversation.id }}
                    onClick={onSelect}
                    className={cn(
                      "flex items-center gap-2 rounded-xl px-3 py-2 pr-9 text-[13.5px] transition-colors",
                      isActive
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/85 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                    )}
                  >
                    {conversation.archived ? (
                      <Archive className="size-3.5 shrink-0 opacity-60" />
                    ) : (
                      <MessageSquare className="size-3.5 shrink-0 opacity-60" />
                    )}
                    <span className="truncate">{conversation.title}</span>
                  </Link>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        aria-label={`Options for ${conversation.title}`}
                        className={cn(
                          "absolute top-1/2 right-1.5 -translate-y-1/2 rounded-lg opacity-0 transition-opacity group-hover/item:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100",
                          isActive && "opacity-70",
                        )}
                      >
                        <MoreHorizontal className="size-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44 rounded-2xl">
                      <DropdownMenuItem
                        className="rounded-xl"
                        onSelect={() => onRename(conversation)}
                      >
                        <Pencil className="size-4" /> Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="rounded-xl"
                        onSelect={() => onArchive(conversation)}
                      >
                        <Archive className="size-4" />
                        {conversation.archived ? "Unarchive" : "Archive"}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="rounded-xl text-destructive focus:text-destructive"
                        onSelect={() => onDelete(conversation)}
                      >
                        <Trash2 className="size-4" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
