import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "@/api/http";
import { NovaWordmark } from "@/components/nova/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApp } from "@/store/app-store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Nova AI" },
      {
        name: "description",
        content: "Sign in to Nova AI to continue your conversations.",
      },
      { property: "og:title", content: "Sign in — Nova AI" },
      { property: "og:description", content: "Continue to your Nova AI workspace." },
    ],
  }),
  component: AuthPage,
});

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type FieldErrors = {
  email?: string;
  password?: string;
};

/** Maps a transport error to a message that is safe and useful for the user. */
function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Incorrect email or password.";
    if (error.status === 403) return "This account is inactive. Contact your administrator.";
    if (error.isNetworkError) return "Can't reach the server. Check your connection and retry.";
    if (error.isServerError) return "Something went wrong on our end. Please try again.";
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

function AuthPage() {
  const navigate = useNavigate();
  const { auth, logIn, hydrated } = useApp();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (hydrated && auth.signedIn) void navigate({ to: "/", replace: true });
  }, [hydrated, auth.signedIn, navigate]);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    const trimmedEmail = email.trim();
    if (!trimmedEmail) next.email = "Email is required.";
    else if (!EMAIL_PATTERN.test(trimmedEmail)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    return next;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);

    const errors = validate();
    setFieldErrors(errors);
    if (errors.email || errors.password) return;

    setPending(true);
    try {
      await logIn(email, password);
      void navigate({ to: "/", replace: true });
    } catch (error) {
      setFormError(messageForError(error));
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <NovaWordmark />
          <h1 className="mt-8 text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Sign in to continue to your workspace.
          </p>

          <form className="mt-7 space-y-4" onSubmit={handleSubmit} noValidate>
            {formError ? (
              <div
                role="alert"
                className="rounded-xl border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive"
              >
                {formError}
              </div>
            ) : null}

            <div className="space-y-1.5">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                disabled={pending}
                aria-invalid={fieldErrors.email ? true : undefined}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (fieldErrors.email) setFieldErrors(({ email: _e, ...rest }) => rest);
                }}
                className={cn(
                  "h-11 rounded-xl",
                  fieldErrors.email && "border-destructive focus-visible:ring-destructive/40",
                )}
              />
              {fieldErrors.email ? (
                <p id="email-error" className="text-xs text-destructive">
                  {fieldErrors.email}
                </p>
              ) : null}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  disabled={pending}
                  aria-invalid={fieldErrors.password ? true : undefined}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    if (fieldErrors.password) setFieldErrors(({ password: _p, ...rest }) => rest);
                  }}
                  className={cn(
                    "h-11 rounded-xl pr-11",
                    fieldErrors.password && "border-destructive focus-visible:ring-destructive/40",
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  disabled={pending}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center px-3.5 text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {fieldErrors.password ? (
                <p id="password-error" className="text-xs text-destructive">
                  {fieldErrors.password}
                </p>
              ) : null}
            </div>

            <Button
              type="submit"
              disabled={pending}
              className="h-11 w-full gap-2 rounded-xl bg-brand text-brand-foreground hover:bg-brand/90"
            >
              {pending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </form>

          <p className="mt-8 text-xs text-muted-foreground">
            By continuing you agree to the terms of service and privacy policy.
          </p>
        </div>
      </div>

      <div className="relative hidden overflow-hidden border-l bg-surface-strong lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,var(--color-brand-soft),transparent_60%)]" />
        <div className="relative flex h-full flex-col justify-center px-14">
          <blockquote className="max-w-md text-xl leading-snug font-medium tracking-tight">
            “Nova turned a folder of messy research notes into a decision memo in a single
            afternoon.”
          </blockquote>
          <p className="mt-4 text-sm text-muted-foreground">
            Priya Raman · Head of Product Research, Lumen Labs
          </p>
          <dl className="mt-12 grid grid-cols-3 gap-6 text-sm">
            {[
              ["4.2M", "messages sent"],
              ["68%", "faster drafts"],
              ["120+", "file types"],
            ].map(([value, label]) => (
              <div key={label}>
                <dt className="text-2xl font-semibold tracking-tight">{value}</dt>
                <dd className="text-xs text-muted-foreground">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}
