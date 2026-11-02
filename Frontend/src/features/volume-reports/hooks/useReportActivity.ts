"use client";

import { useEffect, useRef, useState } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import type { ActivityItem } from "../types";

const VISIBLE_MS = 2000;
const HIDDEN_MS = 15000;

/** Timeline of what the report jobs did. Loads the full history from the server on mount (so it survives leaving the page),
 *  then follows new events with a cursor while `active`; one last fetch runs when `active` turns off to catch the final events. */
export function useReportActivity(reportId: string, active: boolean) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const cursor = useRef(0);
  const reportRef = useRef(reportId);

  useEffect(() => {
    if (reportRef.current !== reportId) { reportRef.current = reportId; cursor.current = 0; setItems([]); setLoaded(false); }
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;

    const tick = async () => {
      try {
        const page = await volumeReportApi.activity(reportId, cursor.current);
        if (stopped) return;
        failures = 0;
        const newest = page.items.at(-1);
        if (newest) {
          cursor.current = newest.id;
          setItems((prev) => [...prev, ...page.items]);
        }
        setLoaded(true);
      } catch {
        failures += 1;
        if (failures >= 5) { if (!stopped) setLoaded(true); return; }
      }
      if (active && !stopped) timer = setTimeout(() => void tick(), document.visibilityState === "visible" ? VISIBLE_MS : HIDDEN_MS);
    };
    void tick();
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, [reportId, active]);

  return { items, loaded };
}
