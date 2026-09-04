import { useEffect } from "react";

export interface ChatShortcutHandlers {
  onSearch: () => void;
  onNewChat: () => void;
  onToggleSidebar: () => void;
}

/** Cmd/Ctrl+K search, Cmd/Ctrl+Shift+O new chat, Cmd/Ctrl+\ sidebar toggle. */
export function useChatShortcuts({
  onSearch,
  onNewChat,
  onToggleSidebar,
}: ChatShortcutHandlers): void {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const meta = event.metaKey || event.ctrlKey;
      if (!meta) return;
      const key = event.key.toLowerCase();
      if (key === "k") {
        event.preventDefault();
        onSearch();
      } else if (event.shiftKey && key === "o") {
        event.preventDefault();
        onNewChat();
      } else if (event.key === "\\") {
        event.preventDefault();
        onToggleSidebar();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSearch, onNewChat, onToggleSidebar]);
}
