import { Bot, Lock, MessagesSquare, SlidersHorizontal, User } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { MODELS, type Settings } from "@/lib/types";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { id: "general", label: "General", icon: SlidersHorizontal },
  { id: "ai", label: "AI preferences", icon: Bot },
  { id: "personalization", label: "Personalization", icon: User },
  { id: "chat", label: "Chat", icon: MessagesSquare },
  { id: "privacy", label: "Privacy", icon: Lock },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function Row({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        {description ? (
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  settings: Settings;
  onSave: (settings: Settings) => void;
  onClearAll: () => void;
}

export function SettingsDialog({
  open,
  onOpenChange,
  settings,
  onSave,
  onClearAll,
}: SettingsDialogProps) {
  const [section, setSection] = useState<SectionId>("general");
  const [draft, setDraft] = useState<Settings>(settings);

  useEffect(() => {
    if (open) setDraft(settings);
  }, [open, settings]);

  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setDraft((prev) => ({ ...prev, [key]: value }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] gap-0 overflow-hidden rounded-3xl p-0 sm:max-w-3xl">
        <DialogHeader className="border-b px-5 py-4">
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Preferences are stored locally in this browser for the preview.
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-col sm:flex-row">
          <nav className="flex gap-1 overflow-x-auto border-b p-2 sm:w-52 sm:flex-col sm:border-r sm:border-b-0">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setSection(id)}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-left text-[13.5px] transition-colors",
                  section === id
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon className="size-4" /> {label}
              </button>
            ))}
          </nav>

          <div className="scrollbar-slim max-h-[52vh] min-w-0 flex-1 overflow-y-auto px-5 py-3">
            {section === "general" ? (
              <div className="divide-y">
                <Row label="Theme" description="Match the system or pick a fixed appearance.">
                  <Select
                    value={draft.theme}
                    onValueChange={(value) => set("theme", value as Settings["theme"])}
                  >
                    <SelectTrigger className="w-36 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="system">System</SelectItem>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                    </SelectContent>
                  </Select>
                </Row>
                <Row label="Language">
                  <Select value={draft.language} onValueChange={(value) => set("language", value)}>
                    <SelectTrigger className="w-36 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en-US">English (US)</SelectItem>
                      <SelectItem value="en-GB">English (UK)</SelectItem>
                      <SelectItem value="de-DE">Deutsch</SelectItem>
                      <SelectItem value="fr-FR">Français</SelectItem>
                      <SelectItem value="ja-JP">日本語</SelectItem>
                    </SelectContent>
                  </Select>
                </Row>
                <Row label="Compact mode" description="Tighter spacing in the transcript.">
                  <Switch
                    checked={draft.compactMode}
                    onCheckedChange={(value) => set("compactMode", value)}
                  />
                </Row>
                <Row label="Animations" description="Motion for streaming and hover states.">
                  <Switch
                    checked={draft.animations}
                    onCheckedChange={(value) => set("animations", value)}
                  />
                </Row>
              </div>
            ) : null}

            {section === "ai" ? (
              <div className="space-y-4 py-3">
                <div className="space-y-1.5">
                  <Label htmlFor="about-ai">What should Nova know about your work?</Label>
                  <Textarea
                    id="about-ai"
                    value={draft.aboutAi}
                    onChange={(event) => set("aboutAi", event.target.value)}
                    rows={3}
                    className="rounded-2xl"
                    placeholder="I lead a product team at a fintech startup…"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="guidance">How should Nova respond?</Label>
                  <Textarea
                    id="guidance"
                    value={draft.responseGuidance}
                    onChange={(event) => set("responseGuidance", event.target.value)}
                    rows={3}
                    className="rounded-2xl"
                    placeholder="Lead with the answer, then the reasoning…"
                  />
                </div>
                <Separator />
                <Row label="Response length">
                  <Select
                    value={draft.responseStyle}
                    onValueChange={(value) =>
                      set("responseStyle", value as Settings["responseStyle"])
                    }
                  >
                    <SelectTrigger className="w-40 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="concise">Concise</SelectItem>
                      <SelectItem value="balanced">Balanced</SelectItem>
                      <SelectItem value="detailed">Detailed</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </Row>
                <Row label="Tone">
                  <Select
                    value={draft.tone}
                    onValueChange={(value) => set("tone", value as Settings["tone"])}
                  >
                    <SelectTrigger className="w-40 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="professional">Professional</SelectItem>
                      <SelectItem value="friendly">Friendly</SelectItem>
                      <SelectItem value="casual">Casual</SelectItem>
                      <SelectItem value="technical">Technical</SelectItem>
                    </SelectContent>
                  </Select>
                </Row>
              </div>
            ) : null}

            {section === "personalization" ? (
              <div className="space-y-4 py-3">
                <div className="space-y-1.5">
                  <Label htmlFor="about-me">About me</Label>
                  <Textarea
                    id="about-me"
                    value={draft.aboutMe}
                    onChange={(event) => set("aboutMe", event.target.value)}
                    rows={3}
                    className="rounded-2xl"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="prefs">My preferences</Label>
                  <Textarea
                    id="prefs"
                    value={draft.myPreferences}
                    onChange={(event) => set("myPreferences", event.target.value)}
                    rows={3}
                    className="rounded-2xl"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="instructions">Custom instructions</Label>
                  <Textarea
                    id="instructions"
                    value={draft.instructions}
                    onChange={(event) => set("instructions", event.target.value)}
                    rows={3}
                    className="rounded-2xl"
                  />
                </div>
              </div>
            ) : null}

            {section === "chat" ? (
              <div className="divide-y">
                <Row label="Default model">
                  <Select
                    value={draft.defaultModel}
                    onValueChange={(value) =>
                      set("defaultModel", value as Settings["defaultModel"])
                    }
                  >
                    <SelectTrigger className="w-40 rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODELS.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          {model.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Row>
                <Row label="Enter to send" description="Off: Shift + Enter sends instead.">
                  <Switch
                    checked={draft.enterToSend}
                    onCheckedChange={(value) => set("enterToSend", value)}
                  />
                </Row>
                <Row label="Show timestamps">
                  <Switch
                    checked={draft.showTimestamps}
                    onCheckedChange={(value) => set("showTimestamps", value)}
                  />
                </Row>
                <Row label="Auto-scroll while streaming">
                  <Switch
                    checked={draft.autoScroll}
                    onCheckedChange={(value) => set("autoScroll", value)}
                  />
                </Row>
                <Row label="Save chats in this browser">
                  <Switch
                    checked={draft.saveHistory}
                    onCheckedChange={(value) => set("saveHistory", value)}
                  />
                </Row>
              </div>
            ) : null}

            {section === "privacy" ? (
              <div className="divide-y">
                <Row label="Chat history" description="Turn off to stop keeping conversations.">
                  <Switch
                    checked={draft.chatHistoryEnabled}
                    onCheckedChange={(value) => set("chatHistoryEnabled", value)}
                  />
                </Row>
                <Row label="Help improve Nova" description="Simulated in this preview.">
                  <Switch
                    checked={draft.improveAi}
                    onCheckedChange={(value) => set("improveAi", value)}
                  />
                </Row>
                <Row label="Remember preferences">
                  <Switch
                    checked={draft.rememberPreferences}
                    onCheckedChange={(value) => set("rememberPreferences", value)}
                  />
                </Row>
                <div className="py-4">
                  <Button
                    variant="outline"
                    className="rounded-xl text-destructive hover:text-destructive"
                    onClick={() => {
                      onClearAll();
                      onOpenChange(false);
                    }}
                  >
                    Delete all chats
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <DialogFooter className="border-t px-5 py-3">
          <Button variant="ghost" className="rounded-xl" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="rounded-xl bg-brand text-brand-foreground hover:bg-brand/90"
            onClick={() => {
              onSave(draft);
              onOpenChange(false);
              toast.success("Settings saved");
            }}
          >
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
