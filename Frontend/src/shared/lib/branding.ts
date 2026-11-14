import { cache } from "react";
import { connection } from "next/server";
import type { Branding } from "@/shared/types";

/** Shown only while the backend cannot be reached (the CSS variables in globals.css hold the matching default colours). */
export const FALLBACK_BRANDING: Omit<Branding, "palette"> & { palette: null } = {
  name: "سازمان",
  short_name: "سازمان",
  app_title: "دستیار هوشمند سازمانی",
  description: "دستیار داخلی سازمان، متصل به اسناد و قراردادها",
  tagline: "دستیار هوشمند سازمانی",
  product_label: "ORBIT WORKSPACE",
  login_headline: "هر سؤالی درباره‌ی اسناد سازمان داری، همین‌جا بپرس.",
  login_footer: "ابزار داخلی کارکنان • دسترسی فقط با حساب سازمانی",
  colors: { brand: "#3446b8", accent: "#e8c523", highlight: "#25b8b4" },
  palette: null,
  logo_url: null,
  updated_at: null,
};

export type ResolvedBranding = Omit<Branding, "palette"> & { palette: Branding["palette"] | null };

/** The server's own address of the API: the browser-facing NEXT_PUBLIC_API_URL can be a relative path (/api/v1) behind the proxy. */
function internalApiUrl(): string {
  return (process.env.INTERNAL_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
}

/** Server-side, once per request (React `cache` dedupes layout + generateMetadata). Never throws: the app must render without it. */
export const getBranding = cache(async (): Promise<ResolvedBranding> => {
  await connection(); // per-request: a branding change shows up on the next page load, never from a build-time snapshot
  try {
    const response = await fetch(`${internalApiUrl()}/branding`, { cache: "no-store", signal: AbortSignal.timeout(2500) });
    if (!response.ok) return FALLBACK_BRANDING;
    return (await response.json()) as Branding;
  } catch {
    return FALLBACK_BRANDING;
  }
});

/** `:root[data-brand]{--brand-500: 52 70 184; ...}` — overrides the defaults in globals.css. Values come from the backend, which only
 *  emits validated `r g b` triplets, but are re-checked here so nothing else can ever reach the stylesheet. */
export function brandingCss(palette: Branding["palette"] | null): string {
  if (!palette) return "";
  const triplet = /^\d{1,3} \d{1,3} \d{1,3}$/;
  const lines: string[] = [];
  for (const group of ["brand", "accent", "teal"] as const) {
    for (const [shade, value] of Object.entries(palette[group] ?? {})) {
      if (/^\d{2,3}$/.test(shade) && triplet.test(value)) lines.push(`--${group}-${shade}:${value}`);
    }
  }
  if (triplet.test(palette.ground?.base ?? "")) lines.push(`--ground:${palette.ground.base}`);
  if (triplet.test(palette.ground?.button ?? "")) lines.push(`--ground-button:${palette.ground.button}`);
  return lines.length ? `:root[data-brand]{${lines.join(";")}}` : "";
}
