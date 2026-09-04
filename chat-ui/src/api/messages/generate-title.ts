/**
 * Optimistic thread title.
 *
 * Shown immediately when a user sends the first message, before the backend
 * returns the real title in the stream's `meta` event. Purely local — no
 * network — so the sidebar never shows a blank "New chat" mid-send.
 */
export function optimisticTitle(prompt: string): string {
  const clean = prompt.replace(/\s+/g, " ").trim();
  if (!clean) return "New chat";
  const words = clean.split(" ").slice(0, 6).join(" ");
  const title = words.charAt(0).toUpperCase() + words.slice(1);
  return title.length < clean.length ? `${title}…` : title;
}
