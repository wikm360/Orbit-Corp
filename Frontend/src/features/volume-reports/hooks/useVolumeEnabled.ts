"use client";

import { useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";

import { probeVolumeReports } from "../api/volumeReportApi";

const cache = new Map<string, Promise<boolean>>();

/** `null` while unknown, then true/false. Cached per session token so the sidebar and pages share one probe. */
export function useVolumeEnabled(): boolean | null {
  const token = useAuthStore((s) => s.token);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  useEffect(() => {
    if (!token) return;
    let live = true;
    if (!cache.has(token)) cache.set(token, probeVolumeReports());
    cache.get(token)!.then((value) => { if (live) setEnabled(value); });
    return () => { live = false; };
  }, [token]);
  return enabled;
}
