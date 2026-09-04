import type { UserProfile } from "./types";

export function initialsFrom(name: string): string {
  return (
    name
      .split(" ")
      .map((part) => part.charAt(0))
      .slice(0, 2)
      .join("")
      .toUpperCase() || "NA"
  );
}

/** Derives a display profile from an email address (used until a real API returns one). */
export function profileFromEmail(email: string, name?: string): UserProfile {
  const clean = email.trim().toLowerCase();
  const derived =
    name?.trim() ||
    clean
      .split("@")[0]
      ?.split(/[._-]/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ") ||
    "Nova User";

  return {
    name: derived,
    email: clean || "demo@novalabs.io",
    initials: initialsFrom(derived),
    plan: "Nova Plus",
  };
}
