"use client";

import { cn } from "@/shared/lib/utils";
import { useBranding } from "./BrandingProvider";

/** The organisation's logo, or — until one is uploaded — the first letter of its name on the brand colour. Plain <img>: the file
 *  is served by the API (already cache-busted by ?v=), so next/image's optimiser and remote-host config are not needed. */
export function BrandLogo({ className, rounded = "rounded-xl" }: { className?: string; rounded?: string }) {
  const branding = useBranding();
  if (branding.logo_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={branding.logo_url} alt="" className={cn("object-contain", rounded, className)} />;
  }
  const letter = (branding.short_name || branding.name).trim().slice(0, 1);
  return <span aria-hidden className={cn("grid place-items-center bg-brand-600 font-bold text-white", rounded, className)}>{letter}</span>;
}
