const PREFIX = "nova-ai:v1:";

export const STORAGE_KEYS = {
  conversations: `${PREFIX}conversations`,
  settings: `${PREFIX}settings`,
  auth: `${PREFIX}auth`,
  authToken: `${PREFIX}auth-token`,
  sidebar: `${PREFIX}sidebar-collapsed`,
} as const;

export function readLocal<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function writeLocal(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota or privacy mode — mock app can continue without persistence */
  }
}

export function removeLocal(key: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
