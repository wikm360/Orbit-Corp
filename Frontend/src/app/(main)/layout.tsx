"use client";

import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { AppSidebar } from "@/shared/components/layout/AppSidebar";
import { AUTH_UNAUTHORIZED_EVENT } from "@/shared/lib/apiClient";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, logout, hasHydrated } = useAuthStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (hasHydrated && !token) router.replace("/login");
  }, [hasHydrated, token, router]);

  useEffect(() => {
    const handleUnauthorized = () => logout();
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [logout]);

  useEffect(() => {
    if (hasHydrated && token && pathname.startsWith("/admin") && user?.role !== "admin") {
      router.replace("/chat");
    }
  }, [hasHydrated, pathname, router, token, user?.role]);

  if (
    !hasHydrated ||
    !token ||
    (pathname.startsWith("/admin") && user?.role !== "admin")
  ) {
    return (
      <div className="grid min-h-screen place-items-center bg-white text-sm text-gray-500">
        در حال آماده‌سازی...
      </div>
    );
  }

  function toggleSidebar() {
    setIsSidebarCollapsed((current) => !current);
  }

  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-white">
      {isSidebarOpen && (
        <button
          type="button"
          aria-label="بستن نوار کناری"
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <AppSidebar
        user={user}
        isOpen={isSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        onClose={() => setIsSidebarOpen(false)}
        onToggleCollapse={toggleSidebar}
        onLogout={logout}
      />

      <div className="flex min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-black/[0.06] px-3 md:hidden">
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            className="rounded-xl p-2 text-gray-700 transition hover:bg-gray-100"
            aria-label="باز کردن نوار کناری"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <Image src="/logo.jpg" alt="" width={28} height={28} className="h-7 w-7 rounded-lg object-cover" />
            <span className="text-sm font-semibold text-gray-900">محور گستر</span>
          </div>
          <button
            type="button"
            onClick={() => router.push(`/chat?new=${Date.now()}`)}
            className="rounded-xl p-2 text-gray-700 transition hover:bg-gray-100"
            aria-label="گفتگوی جدید"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" d="M12 5v14M5 12h14" />
            </svg>
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
