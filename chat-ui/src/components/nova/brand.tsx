import logo from "@/assets/nova-logo.png";
import { cn } from "@/lib/utils";

export function NovaMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-8 shrink-0 place-items-center rounded-xl bg-brand-soft ring-1 ring-brand/20",
        className,
      )}
    >
      <img src={logo} alt="" width={512} height={512} className="size-5 object-contain" />
    </span>
  );
}

export function NovaWordmark({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <NovaMark />
      <span className="text-[15px] font-semibold tracking-tight">Nova AI</span>
    </span>
  );
}
