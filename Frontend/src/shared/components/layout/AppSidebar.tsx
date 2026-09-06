"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { chatApi } from "@/features/chat/api/chatApi";
import { Conversation } from "@/features/chat/types";
import { User } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

type IconName =
  | "panel"
  | "plus"
  | "chat"
  | "search"
  | "document"
  | "admin"
  | "logout"
  | "close";

const paths: Record<IconName, React.ReactNode> = {
  panel: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  chat: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  document: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h6"/></>,
  admin: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></>,
  logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/></>,
  close: <path d="m18 6-12 12M6 6l12 12"/>,
};

function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("h-5 w-5 shrink-0", className)}
    >
      {paths[name]}
    </svg>
  );
}

const NAV_ITEMS = [
  { href: "/chat", label: "دستیار", icon: "chat" as const },
  { href: "/documents", label: "اسناد", icon: "document" as const },
  { href: "/admin", label: "مدیریت", icon: "admin" as const, adminOnly: true },
];

interface AppSidebarProps {
  user: User | null;
  isOpen: boolean;
  isCollapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
  onLogout: () => void;
}

export function AppSidebar({
  user,
  isOpen,
  isCollapsed,
  onClose,
  onToggleCollapse,
  onLogout,
}: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("conversation");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  const loadConversations = useCallback(async () => {
    if (pathname !== "/chat") return;
    setIsLoading(true);
    try {
      setConversations(await chatApi.listConversations());
      setHasError(false);
    } catch {
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, [pathname]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadConversations(), 0);
    return () => window.clearTimeout(timer);
  }, [activeConversationId, loadConversations]);

  useEffect(() => {
    const refresh = () => void loadConversations();
    window.addEventListener("orbit:conversations-changed", refresh);
    return () => window.removeEventListener("orbit:conversations-changed", refresh);
  }, [loadConversations]);

  const userLabel = user?.full_name?.trim() || user?.email || "حساب کاربری";
  const avatarLetter = userLabel.slice(0, 1).toLocaleUpperCase("fa-IR");

  function startNewConversation() {
    router.push(`/chat?new=${Date.now()}`);
    onClose();
  }

  return (
    <aside
      aria-label="نوار کناری اصلی"
      className={cn(
        "fixed inset-y-0 right-0 z-50 flex w-[286px] flex-col border-l border-black/5 bg-[#f7f7f8] p-2 transition-[transform,width] duration-200 ease-out md:relative md:z-20 md:translate-x-0",
        isOpen ? "translate-x-0 shadow-2xl" : "translate-x-full",
        isCollapsed && "md:w-[72px]"
      )}
    >
      <div className="flex h-11 items-center gap-2 px-1">
        <Link
          href="/chat"
          onClick={onClose}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-2 rounded-xl p-1.5 transition hover:bg-black/[0.04]",
            isCollapsed && "md:justify-center"
          )}
          aria-label="دستیار هوشمند محور گستر"
        >
          <Image src="/logo.jpg" alt="" width={30} height={30} className="h-7 w-7 rounded-lg object-cover" />
          <span className={cn("truncate text-sm font-bold text-gray-900", isCollapsed && "md:hidden")}>محور گستر</span>
        </Link>
        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden rounded-xl p-2 text-gray-600 transition hover:bg-black/[0.06] hover:text-gray-950 md:block"
          aria-label={isCollapsed ? "باز کردن نوار کناری" : "جمع کردن نوار کناری"}
          title={isCollapsed ? "باز کردن نوار کناری" : "جمع کردن نوار کناری"}
        >
          <Icon name="panel" />
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-2 text-gray-600 transition hover:bg-black/[0.06] md:hidden"
          aria-label="بستن نوار کناری"
        >
          <Icon name="close" />
        </button>
      </div>

      <button
        type="button"
        onClick={startNewConversation}
        className={cn(
          "mt-2 flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-gray-900 transition hover:bg-black/[0.055] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300",
          pathname === "/chat" && !activeConversationId && "bg-black/[0.055]",
          isCollapsed && "md:justify-center md:px-0"
        )}
        title={isCollapsed ? "گفتگوی جدید" : undefined}
      >
        <Icon name="plus" />
        <span className={cn(isCollapsed && "md:hidden")}>گفتگوی جدید</span>
      </button>

      <nav aria-label="ناوبری اصلی" className="mt-1 space-y-0.5">
        {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              title={isCollapsed ? item.label : undefined}
              className={cn(
                "flex h-11 items-center gap-3 rounded-xl px-3 text-sm text-gray-700 transition hover:bg-black/[0.055] hover:text-gray-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300",
                isActive && item.href !== "/chat" && "bg-white font-medium text-gray-950 shadow-sm",
                isCollapsed && "md:justify-center md:px-0"
              )}
            >
              <Icon name={item.icon} />
              <span className={cn(isCollapsed && "md:hidden")}>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className={cn("my-3 h-px bg-black/[0.06]", isCollapsed && "md:mx-1")} />

      <div className={cn("min-h-0 flex-1", isCollapsed && "md:hidden")}>
        {pathname === "/chat" ? (
          <div className="flex h-full min-h-0 flex-col">
            <div className="flex items-center justify-between px-3 pb-2">
              <span className="text-xs font-medium text-gray-500">گفتگوهای اخیر</span>
              <Icon name="search" className="h-4 w-4 text-gray-400" />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pb-2">
              {isLoading && conversations.length === 0 && (
                <div className="space-y-2 px-2 py-1" aria-label="در حال دریافت گفتگوها">
                  {[0, 1, 2].map((item) => <div key={item} className="h-8 animate-pulse rounded-lg bg-black/[0.045]" />)}
                </div>
              )}
              {!isLoading && hasError && (
                <button type="button" onClick={() => void loadConversations()} className="w-full rounded-xl px-3 py-3 text-right text-xs leading-5 text-red-600 hover:bg-red-50">
                  دریافت تاریخچه ناموفق بود؛ تلاش دوباره
                </button>
              )}
              {!isLoading && !hasError && conversations.length === 0 && (
                <p className="px-3 py-3 text-xs leading-6 text-gray-400">گفتگوهای شما اینجا نمایش داده می‌شوند.</p>
              )}
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => {
                    router.push(`/chat?conversation=${conversation.id}`);
                    onClose();
                  }}
                  className={cn(
                    "mb-0.5 block w-full truncate rounded-lg px-3 py-2.5 text-right text-[13px] text-gray-700 transition hover:bg-black/[0.055] hover:text-gray-950",
                    conversation.id === activeConversationId && "bg-black/[0.065] font-medium text-gray-950"
                  )}
                >
                  {conversation.title}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="px-3 py-2">
            <p className="text-xs font-medium text-gray-500">فضای کاری سازمان</p>
            <p className="mt-2 text-xs leading-6 text-gray-400">مدیریت دانش، اسناد و دسترسی‌های تیم در یک محیط یکپارچه.</p>
          </div>
        )}
      </div>

      <div className="border-t border-black/[0.06] pt-2">
        <div className={cn("flex items-center gap-2 rounded-xl p-2 hover:bg-black/[0.045]", isCollapsed && "md:justify-center")}>
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gray-900 text-xs font-semibold text-white">{avatarLetter}</span>
          <div className={cn("min-w-0 flex-1", isCollapsed && "md:hidden")}>
            <p className="truncate text-xs font-semibold text-gray-900">{userLabel}</p>
            <p className="mt-0.5 truncate text-[10px] text-gray-500">{user?.role === "admin" ? "مدیر سازمان" : "عضو سازمان"}</p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className={cn("rounded-lg p-2 text-gray-500 transition hover:bg-white hover:text-red-600", isCollapsed && "md:hidden")}
            aria-label="خروج از حساب"
            title="خروج"
          >
            <Icon name="logout" className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
