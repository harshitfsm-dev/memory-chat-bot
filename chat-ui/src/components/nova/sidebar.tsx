import { Link } from "@tanstack/react-router";
import {
  Archive,
  ChevronsLeft,
  HelpCircle,
  LifeBuoy,
  LogOut,
  Moon,
  PenSquare,
  Plus,
  Search,
  Settings,
  Sun,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { NovaMark, NovaWordmark } from "@/components/nova/brand";
import { ChatList } from "@/components/nova/chat-list";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Conversation, UserProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  user: UserProfile;
  collapsed: boolean;
  theme: "light" | "dark";
  searchRef?: React.Ref<HTMLInputElement>;
  onCollapse: () => void;
  onNewChat: () => void;
  onSelect: () => void;
  onRename: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onOpenSettings: () => void;
  onToggleTheme: () => void;
  onSignOut: () => void;
  onCloseMobile?: () => void;
  isMobile?: boolean;
}

export function SidebarRail({
  onExpand,
  onNewChat,
  onOpenSettings,
  user,
}: {
  onExpand: () => void;
  onNewChat: () => void;
  onOpenSettings: () => void;
  user: UserProfile;
}) {
  return (
    <TooltipProvider delayDuration={300}>
      <aside className="hidden w-[60px] shrink-0 flex-col items-center gap-2 border-r bg-sidebar py-3 md:flex">
        <button
          type="button"
          onClick={onExpand}
          aria-label="Expand sidebar"
          className="rounded-xl transition-transform hover:scale-105"
        >
          <NovaMark />
        </button>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="New chat"
              onClick={onNewChat}
              className="mt-1 rounded-xl"
            >
              <PenSquare className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">New chat</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Expand sidebar to search"
              onClick={onExpand}
              className="rounded-xl"
            >
              <Search className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">Search chats</TooltipContent>
        </Tooltip>

        <div className="mt-auto flex flex-col items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Settings"
                onClick={onOpenSettings}
                className="rounded-xl"
              >
                <Settings className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Settings</TooltipContent>
          </Tooltip>
          <Avatar className="size-8">
            <AvatarFallback className="bg-surface-strong text-[11px] font-semibold">
              {user.initials}
            </AvatarFallback>
          </Avatar>
        </div>
      </aside>
    </TooltipProvider>
  );
}

export function Sidebar({
  conversations,
  activeId,
  user,
  theme,
  searchRef,
  onCollapse,
  onNewChat,
  onSelect,
  onRename,
  onDelete,
  onArchive,
  onOpenSettings,
  onToggleTheme,
  onSignOut,
  onCloseMobile,
  isMobile = false,
}: SidebarProps) {
  const [query, setQuery] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return conversations.filter((conversation) => {
      if (conversation.archived !== showArchived) return false;
      if (!q) return true;
      return (
        conversation.title.toLowerCase().includes(q) ||
        conversation.messages.some((message) => message.content.toLowerCase().includes(q))
      );
    });
  }, [conversations, query, showArchived]);

  const archivedCount = conversations.filter((conversation) => conversation.archived).length;

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground md:w-72 md:border-r">
      <div className="flex items-center gap-1 px-3 py-3">
        <Link to="/" onClick={onSelect} className="min-w-0 flex-1">
          <NovaWordmark />
        </Link>
        {isMobile ? (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Close sidebar"
            onClick={onCloseMobile}
            className="rounded-xl"
          >
            <X className="size-4" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Collapse sidebar"
            onClick={onCollapse}
            className="rounded-xl text-muted-foreground"
          >
            <ChevronsLeft className="size-4" />
          </Button>
        )}
      </div>

      <div className="space-y-2 px-3 pb-2">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-2 rounded-xl bg-brand text-brand-foreground shadow-sm hover:bg-brand/90"
        >
          <Plus className="size-4" /> New chat
        </Button>

        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={searchRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search conversations"
            aria-label="Search conversations"
            className="h-9 rounded-xl border-transparent bg-sidebar-accent/70 pl-9 text-[13.5px] placeholder:text-muted-foreground focus-visible:border-input"
          />
        </div>
      </div>

      <nav className="scrollbar-slim min-h-0 flex-1 overflow-y-auto px-1.5 pb-2">
        <ChatList
          conversations={filtered}
          activeId={activeId}
          onSelect={onSelect}
          onRename={onRename}
          onDelete={onDelete}
          onArchive={onArchive}
          emptyLabel={
            query.trim()
              ? `No conversations match “${query.trim()}”`
              : showArchived
                ? "Nothing archived yet"
                : "No conversations yet"
          }
        />
      </nav>

      <div className="border-t p-2">
        {archivedCount > 0 || showArchived ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowArchived((prev) => !prev)}
            className="mb-1 w-full justify-start gap-2 rounded-xl text-[13px] text-muted-foreground"
          >
            <Archive className="size-4" />
            {showArchived ? "Back to chats" : `Archived (${archivedCount})`}
          </Button>
        ) : null}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center gap-2.5 rounded-xl p-2 text-left transition-colors hover:bg-sidebar-accent"
            >
              <Avatar className="size-8">
                <AvatarFallback className="bg-brand-soft text-[11px] font-semibold text-brand">
                  {user.initials}
                </AvatarFallback>
              </Avatar>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13.5px] font-medium">{user.name}</span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {user.email}
                </span>
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="top" className="w-64 rounded-2xl">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
              {user.plan}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="rounded-xl" onSelect={onOpenSettings}>
              <Settings className="size-4" /> Settings
            </DropdownMenuItem>
            <DropdownMenuItem className="rounded-xl" onSelect={onToggleTheme}>
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
              {theme === "dark" ? "Light theme" : "Dark theme"}
            </DropdownMenuItem>
            <DropdownMenuItem
              className="rounded-xl"
              onSelect={() => toast.info("Help center opens in the full product")}
            >
              <HelpCircle className="size-4" /> Help
            </DropdownMenuItem>
            <DropdownMenuItem
              className="rounded-xl"
              onSelect={() => toast.success("Thanks — feedback noted")}
            >
              <LifeBuoy className="size-4" /> Send feedback
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="rounded-xl text-destructive focus:text-destructive"
              onSelect={onSignOut}
            >
              <LogOut className="size-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}

export function SidebarShellClass({ collapsed }: { collapsed: boolean }) {
  return cn("hidden md:flex", collapsed && "md:hidden");
}
