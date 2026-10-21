import clsx from "clsx";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
const styles: Record<Variant, string> = {
  primary: "bg-bordo-700 text-cream-50 hover:bg-bordo-500 active:bg-bordo-900 border border-transparent",
  secondary: "bg-white text-green-700 border border-green-700 hover:bg-green-50",
  ghost: "bg-transparent text-green-700 hover:bg-green-100 border border-transparent",
  danger: "bg-white text-danger border border-danger hover:bg-danger-bg",
};
const sizes = {
  sm: "min-h-11 px-3 text-sm sm:h-9 sm:min-h-0",
  md: "min-h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant; size?: keyof typeof sizes; href?: string; children: ReactNode;
}

export function Button({ variant = "secondary", size = "md", href, className, children, ...rest }: Props) {
  const cls = clsx("motion-control inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none", styles[variant], sizes[size], className);
  return href ? <Link href={href} className={cls}>{children}</Link> : <button className={cls} {...rest}>{children}</button>;
}
