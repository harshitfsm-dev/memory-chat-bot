import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { NovaWordmark } from "@/components/nova/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useApp } from "@/store/app-store";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Nova AI" },
      {
        name: "description",
        content: "Sign in to Nova AI to continue your conversations. Demo sign-in, no account needed.",
      },
      { property: "og:title", content: "Sign in — Nova AI" },
      { property: "og:description", content: "Continue to your Nova AI workspace." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const { auth, signIn, hydrated } = useApp();
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (hydrated && auth.signedIn) navigate({ to: "/", replace: true });
  }, [hydrated, auth.signedIn, navigate]);

  const submit = (value: string) => {
    setPending(true);
    window.setTimeout(() => {
      signIn(value);
      setPending(false);
      void navigate({ to: "/", replace: true });
    }, 700);
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <NovaWordmark />
          <h1 className="mt-8 text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            This is a UI demo — any email signs you in.
          </p>

          <form
            className="mt-7 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (email.trim()) submit(email);
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-11 rounded-xl"
              />
            </div>
            <Button
              type="submit"
              disabled={!email.trim() || pending}
              className="h-11 w-full gap-2 rounded-xl bg-brand text-brand-foreground hover:bg-brand/90"
            >
              {pending ? <Loader2 className="size-4 animate-spin" /> : null}
              Continue
              {!pending ? <ArrowRight className="size-4" /> : null}
            </Button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-[11px] text-muted-foreground uppercase">or</span>
            <Separator className="flex-1" />
          </div>

          <Button
            variant="outline"
            className="h-11 w-full rounded-xl"
            disabled={pending}
            onClick={() => submit("avery.chen@northwind.io")}
          >
            Continue as demo user
          </Button>

          <p className="mt-8 text-xs text-muted-foreground">
            By continuing you agree to the demo terms. No data leaves your browser.
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
