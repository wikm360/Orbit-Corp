"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";

const NAV_ITEMS = [
  { href: "/chat", label: "چت" },
  { href: "/documents", label: "اسناد" },
  { href: "/admin", label: "پنل ادمین", adminOnly: true },
];

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, logout, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (hasHydrated && !token) router.replace("/login");
  }, [hasHydrated, token, router]);

  if (!hasHydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4">
        <nav className="flex gap-1">
          {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-1.5 text-sm ${
                pathname?.startsWith(item.href)
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>{user?.email}</span>
          <button onClick={logout} className="text-brand-600 hover:underline">
            خروج
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}
