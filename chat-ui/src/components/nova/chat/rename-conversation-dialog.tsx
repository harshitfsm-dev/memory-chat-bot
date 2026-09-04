import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { Conversation } from "@/lib/types";

export interface RenameConversationDialogProps {
  conversation: Conversation | null;
  onOpenChange: (open: boolean) => void;
  onRename: (id: string, title: string) => void;
}

export function RenameConversationDialog({
  conversation,
  onOpenChange,
  onRename,
}: RenameConversationDialogProps) {
  const [value, setValue] = useState("");

  useEffect(() => {
    if (conversation) setValue(conversation.title);
  }, [conversation]);

  const commit = () => {
    if (!conversation || !value.trim()) return;
    onRename(conversation.id, value);
    onOpenChange(false);
  };

  return (
    <Dialog open={Boolean(conversation)} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-3xl sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Rename conversation</DialogTitle>
        </DialogHeader>
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="rounded-xl"
          autoFocus
          onKeyDown={(event) => event.key === "Enter" && commit()}
        />
        <DialogFooter>
          <Button variant="ghost" className="rounded-xl" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="rounded-xl bg-brand text-brand-foreground hover:bg-brand/90"
            disabled={!value.trim()}
            onClick={commit}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
