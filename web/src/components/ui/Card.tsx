import clsx from "clsx";
import type { HTMLAttributes } from "react";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("motion-card rounded-xl border border-cream-300 bg-white p-5 shadow-sm", className)} {...rest} />;
}

export function StatCard({ value, label, hint }: { value: string | number; label: string; hint?: string }) {
  return (
    <Card>
      <p className="font-heading text-2xl font-bold text-green-700 sm:text-3xl">{value}</p>
      <p className="mt-1 text-sm text-ink-muted">{label}</p>
      {hint && <p className="mt-2 text-xs text-ink-muted">{hint}</p>}
    </Card>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-5 flex min-w-0 flex-col items-stretch justify-between gap-3 sm:mb-6 sm:flex-row sm:items-end">
      <div className="min-w-0">
        <h1 className="break-words text-2xl font-bold sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-ink-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <Card className="py-10 text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mx-auto mt-1 max-w-sm text-ink-muted">{text}</p>
    </Card>
  );
}
