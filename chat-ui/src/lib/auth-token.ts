/**
 * Bearer token store.
 *
 * The single source of truth for the access token used by the API layer.
 * The HTTP client reads from here to attach the Authorization header, and the
 * auth endpoints write/clear it. Kept separate from the React store so
 * non-component code (the transport seam) can reach the token without a hook.
 */
import { STORAGE_KEYS, readLocal, removeLocal, writeLocal } from "./storage";

let cached: string | null = null;
let hydrated = false;

function hydrate(): void {
  if (hydrated) return;
  cached = readLocal<string>(STORAGE_KEYS.authToken);
  hydrated = true;
}

export function getToken(): string | null {
  hydrate();
  return cached;
}

export function setToken(token: string): void {
  cached = token;
  hydrated = true;
  writeLocal(STORAGE_KEYS.authToken, token);
}

export function clearToken(): void {
  cached = null;
  hydrated = true;
  removeLocal(STORAGE_KEYS.authToken);
}
