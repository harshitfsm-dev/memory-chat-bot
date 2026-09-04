import type { Conversation } from "./types";

export type GroupLabel = "Today" | "Yesterday" | "Previous 7 Days" | "Older";

const GROUP_ORDER: GroupLabel[] = ["Today", "Yesterday", "Previous 7 Days", "Older"];

function startOfDay(date: Date): number {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function groupLabelFor(isoDate: string, now = new Date()): GroupLabel {
  const today = startOfDay(now);
  const day = startOfDay(new Date(isoDate));
  const diffDays = Math.round((today - day) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Previous 7 Days";
  return "Older";
}

export function groupConversations(
  conversations: Conversation[],
  now = new Date(),
): { label: GroupLabel; items: Conversation[] }[] {
  const buckets = new Map<GroupLabel, Conversation[]>();
  for (const conversation of conversations) {
    const label = groupLabelFor(conversation.updatedAt, now);
    const existing = buckets.get(label);
    if (existing) existing.push(conversation);
    else buckets.set(label, [conversation]);
  }
  return GROUP_ORDER.filter((label) => (buckets.get(label)?.length ?? 0) > 0).map((label) => ({
    label,
    items: [...(buckets.get(label) ?? [])].sort(
      (a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt),
    ),
  }));
}

export function formatTime(isoDate: string): string {
  return new Date(isoDate).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatDateTime(isoDate: string): string {
  const date = new Date(isoDate);
  const label = groupLabelFor(isoDate);
  if (label === "Today") return formatTime(isoDate);
  if (label === "Yesterday") return `Yesterday ${formatTime(isoDate)}`;
  return `${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })} · ${formatTime(isoDate)}`;
}
