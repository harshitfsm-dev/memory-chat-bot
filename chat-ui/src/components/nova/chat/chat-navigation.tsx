import type { RefObject } from "react";

import { Sidebar, SidebarRail } from "@/components/nova/sidebar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import type { Conversation, UserProfile } from "@/lib/types";

export interface ChatNavigationProps {
  conversations: Conversation[];
  activeId: string | null;
  user: UserProfile;
  theme: "light" | "dark";
  collapsed: boolean;
  mobileOpen: boolean;
  searchRef: RefObject<HTMLInputElement | null>;
  onMobileOpenChange: (open: boolean) => void;
  onCollapse: () => void;
  onExpand: () => void;
  onNewChat: () => void;
  onRename: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onOpenSettings: () => void;
  onToggleTheme: () => void;
  onSignOut: () => void;
}

/** Desktop rail/sidebar plus the mobile sheet, sharing one set of handlers. */
export function ChatNavigation({
  conversations,
  activeId,
  user,
  theme,
  collapsed,
  mobileOpen,
  searchRef,
  onMobileOpenChange,
  onCollapse,
  onExpand,
  onNewChat,
  onRename,
  onDelete,
  onArchive,
  onOpenSettings,
  onToggleTheme,
  onSignOut,
}: ChatNavigationProps) {
  const sidebarProps = {
    conversations,
    activeId,
    user,
    collapsed,
    theme,
    onCollapse,
    onNewChat,
    onRename,
    onDelete,
    onArchive,
    onOpenSettings,
    onToggleTheme,
    onSignOut,
    onSelect: () => onMobileOpenChange(false),
  };

  return (
    <>
      {collapsed ? (
        <SidebarRail
          onExpand={onExpand}
          onNewChat={onNewChat}
          onOpenSettings={onOpenSettings}
          user={user}
        />
      ) : (
        <div className="hidden md:block">
          <Sidebar {...sidebarProps} searchRef={searchRef} />
        </div>
      )}

      <Sheet open={mobileOpen} onOpenChange={onMobileOpenChange}>
        <SheetContent side="left" className="w-[85vw] max-w-80 p-0 md:hidden">
          <SheetTitle className="sr-only">Conversations</SheetTitle>
          <Sidebar
            {...sidebarProps}
            isMobile
            searchRef={searchRef}
            onCloseMobile={() => onMobileOpenChange(false)}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
