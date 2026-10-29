"use client";
import { UserButton } from "@clerk/nextjs";
import clsx from "clsx";
import {
  Award,
  BarChart3,
  BookOpen,
  BookMarked,
  Bot,
  ClipboardCheck,
  ClipboardList,
  CalendarDays,
  FileCheck,
  FileText,
  GraduationCap,
  Info,
  IdCard,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  MessagesSquare,
  Presentation,
  Sparkles,
  ShieldCheck,
  Trophy,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { demoSignOut } from "@/lib/actions";
import { ToastProvider } from "@/components/ui/Toast";
import { AarshFloatingWidget } from "@/components/features/AarshFloatingWidget";
import ActivityTracker from "@/components/features/ActivityTracker";

type Role = "student" | "teacher" | "admin";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

const NAV: Record<Role, NavItem[]> = {
  student: [
    { href: "/student/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/student/courses", label: "Choose Courses", icon: BookOpen },
    { href: "/student/exams", label: "Exams", icon: FileText },
    { href: "/student/tasks", label: "My Tasks & Points", icon: ClipboardList },
    { href: "/student/results", label: "My Results", icon: FileCheck },
    { href: "/student/certificates", label: "Certificates", icon: Award },
    { href: "/planner", label: "Learn Planner", icon: CalendarDays },
    { href: "/student/profile", label: "Virtual ID Card", icon: IdCard },
    { href: "/ranking", label: "Live Ranking", icon: Trophy, badge: "Top 4" },
    { href: "/notices", label: "Notice Board", icon: Megaphone },
    { href: "/community-chat", label: "Community Chat", icon: MessagesSquare },
    { href: "/whiteboard", label: "Live Classroom", icon: Presentation },
    { href: "/assistant", label: "Aarsh AI", icon: Bot, badge: "AI" },
  ],
  teacher: [
    { href: "/teacher/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/teacher/courses/new", label: "Create Course", icon: BookMarked },
    { href: "/teacher/exams", label: "Manage Exams", icon: FileText },
    { href: "/teacher/tasks", label: "Task Approvals", icon: ClipboardCheck },
    { href: "/planner", label: "Learn Planner", icon: CalendarDays },
    { href: "/ranking", label: "Live Ranking", icon: Trophy },
    { href: "/notices", label: "Notices", icon: Megaphone },
    { href: "/community-chat", label: "Community Chat", icon: MessagesSquare },
    { href: "/whiteboard", label: "Live Classroom", icon: Presentation },
    { href: "/assistant", label: "Aarsh AI", icon: Bot },
  ],
  admin: [
    { href: "/admin/users", label: "User Control", icon: Users },
    { href: "/admin/courses", label: "Course Control", icon: BookMarked },
    { href: "/admin/progress", label: "Progress Check", icon: BookOpen },
    { href: "/admin/analytics", label: "Live Analytics", icon: BarChart3 },
    { href: "/admin/security", label: "Security Monitor", icon: ShieldCheck },
    { href: "/admin/notices", label: "Notice Control", icon: Megaphone },
    { href: "/planner", label: "Learn Planner", icon: CalendarDays },
    { href: "/ranking", label: "Live Ranking", icon: Trophy },
    { href: "/community-chat", label: "Community Chat", icon: MessagesSquare },
    { href: "/whiteboard", label: "Live Classroom", icon: Presentation },
    { href: "/assistant", label: "Aarsh AI", icon: Bot },
  ],
};

export function Shell({ role, name, demo, children }: { role: Role; name: string; demo: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const path = usePathname();
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setOpen(false);
  }, [path]);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const nav = (
    <nav id="portal-navigation" aria-label="Main Navigation" className={clsx("flex flex-col gap-1.5 py-4", collapsed ? "px-2" : "px-3")}>
      {[...NAV[role], { href: "/about", label: "About", icon: Info }].map(({ href, label, icon: Icon, badge }) => {
        const active = path === href || path.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            title={collapsed ? label : undefined}
            className={clsx(
              "group flex h-11 items-center rounded-lg text-sm transition-all duration-150",
              collapsed ? "justify-center px-0" : "gap-3 px-3.5",
              active
                ? "bg-cream-200 text-green-900 font-semibold shadow-sm"
                : "text-cream-100/90 hover:bg-green-600 hover:text-cream-50"
            )}
          >
            <Icon
              size={19}
              strokeWidth={active ? 2.25 : 1.75}
              className={clsx("transition-transform duration-150 group-hover:scale-110", active ? "text-green-900" : "text-cream-200/90 group-hover:text-cream-100")}
              aria-hidden
            />
            <span className={clsx("truncate", collapsed && "lg:hidden")}>{label}</span>

            {badge && !active && !collapsed && (
              <span className="ml-auto rounded-full bg-green-900/60 px-2 py-0.5 text-[10px] font-medium text-cream-200">
                {badge}
              </span>
            )}

            {/* In the design system, active pill has a small bordo-700 dot inside the cream pill */}
            {active && (
              <span
                className={clsx("ml-auto h-2 w-2 rounded-full bg-bordo-700 shadow-sm", collapsed && "hidden")}
                title="Current page"
                aria-hidden
              />
            )}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <ToastProvider>
      <ActivityTracker role={role} />
      <div className={clsx("min-h-dvh bg-cream-50 transition-[padding] duration-200", collapsed ? "lg:pl-16" : "lg:pl-64")}>
        {/* Deep Green Heritage Sidebar (30% secondary brand structure) */}
        <aside
          className={clsx(
            "fixed inset-y-0 left-0 z-40 flex w-[min(18rem,calc(100vw-2.5rem))] flex-col bg-green-700 pb-[env(safe-area-inset-bottom)] text-cream-100 shadow-lg transition-[transform,width] duration-200 lg:translate-x-0",
            collapsed ? "lg:w-16" : "lg:w-64",
            open ? "translate-x-0" : "-translate-x-full"
          )}
          aria-label="Main menu"
        >
          {/* Logo & Crest */}
          <div className={clsx("flex h-16 items-center border-b border-green-900/40", collapsed ? "justify-center px-2" : "justify-between px-5")}>
            <Link href="/" className={clsx("flex items-center", collapsed ? "justify-center" : "gap-2.5")} title={collapsed ? "SiliconBrains University" : undefined}>
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-cream-200 text-green-900 shadow-sm">
                <GraduationCap size={20} aria-hidden />
              </span>
              <div className={clsx(collapsed && "lg:hidden")}>
                <span className="block font-heading text-lg font-bold leading-tight text-cream-50">
                  SiliconBrains
                </span>
                <span className="block text-[10px] font-medium uppercase tracking-wider text-cream-300">
                  University
                </span>
              </div>
            </Link>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg p-1 text-cream-200 hover:bg-green-600 lg:hidden"
              aria-label="Close menu"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation Links */}
          <div className="flex-1 overflow-y-auto py-2">
            {nav}
          </div>

          {/* User Status Footer in Sidebar */}
          <div className={clsx("border-t border-green-900/40", collapsed ? "p-2" : "p-3.5")}>
            <div className={clsx("flex items-center rounded-lg bg-green-900/40", collapsed ? "justify-center p-2" : "gap-3 p-2.5")} title={collapsed ? `${name} — ${role}` : undefined}>
              <div className="grid h-8 w-8 place-items-center rounded-full bg-cream-200 font-heading text-xs font-bold text-green-900">
                {name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
              </div>
              <div className={clsx("min-w-0 flex-1", collapsed && "lg:hidden")}>
                <p className="truncate text-xs font-semibold text-cream-50">{name}</p>
                <p className="text-[10px] uppercase tracking-wider text-cream-300">{role}</p>
              </div>
            </div>
          </div>
        </aside>

        {/* Mobile backdrop */}
        {open && (
          <button
            type="button"
            aria-label="Close menu"
            className="fixed inset-0 z-30 bg-green-900/60 backdrop-blur-sm lg:hidden"
            onClick={() => setOpen(false)}
          />
        )}

        {/* Top Header Bar */}
        <header className="sticky top-0 z-20 flex min-h-16 items-center gap-2 border-b border-cream-300 bg-white/95 px-3 pt-[env(safe-area-inset-top)] backdrop-blur sm:gap-3 sm:px-6">
          <button
            ref={menuButtonRef}
            type="button"
            aria-expanded={open}
            aria-controls="portal-navigation"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-green-700 hover:bg-green-50 lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen(!open)}
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
          <button type="button" onClick={() => setCollapsed((value) => !value)} className="hidden h-11 w-11 shrink-0 place-items-center rounded-lg text-green-700 hover:bg-green-50 lg:grid" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
          </button>

          {/* Quick breadcrumb / brand hint */}
          <div className="flex min-w-0 items-center gap-1.5 text-sm sm:gap-2">
            <span className="hidden font-heading font-semibold capitalize text-green-900 sm:inline">
              {role} Portal
            </span>
            <span className="hidden text-cream-300 sm:inline">/</span>
            <span className="truncate text-xs text-ink-muted sm:text-sm">
              {NAV[role].find((n) => path === n.href || path.startsWith(n.href + "/"))?.label ?? "Overview"}
            </span>
          </div>

          <div className="min-w-0 flex-1" />

          {/* AI Shortcut button */}
          <Link
            href="/assistant"
            className="hidden items-center gap-1.5 rounded-full border border-green-700/30 bg-green-50 px-3 py-1 text-xs font-medium text-green-700 transition-colors hover:bg-green-100 sm:inline-flex"
          >
            <Sparkles size={14} className="text-bordo-700" />
            <span>Aarsh AI</span>
          </Link>

          {/* User profile dropdown / signout */}
          <div className="hidden text-right sm:block">
            <p className="text-sm font-semibold text-green-900">{name}</p>
            <p className="text-[11px] capitalize text-ink-muted">{role}</p>
          </div>

          {demo ? (
            <form action={demoSignOut}>
              <button
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-cream-300 px-3 text-xs font-semibold text-green-700 transition-colors hover:bg-cream-100"
              >
                <LogOut size={14} aria-hidden />
                <span>Sign out</span>
              </button>
            </form>
          ) : (
            <UserButton afterSignOutUrl="/" />
          )}
        </header>

        {/* Main Content Area */}
        <main className="mx-auto w-full max-w-6xl px-3 py-5 sm:px-6 sm:py-8">
          <div key={path} className="page-enter">
            {children}
          </div>
        </main>

        {/* Floating Aarsh AI Assistant accessible on all pages */}
        <AarshFloatingWidget userName={name} />
      </div>
    </ToastProvider>
  );
}
