"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";

export default function RootPage() {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  useEffect(() => {
    if (!hasHydrated) return;
    router.replace(token ? "/chat" : "/login");
  }, [hasHydrated, token, router]);

  return null;
}
