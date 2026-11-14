"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { ResolvedBranding } from "@/shared/lib/branding";

const BrandingContext = createContext<ResolvedBranding | null>(null);

/** Gives client components the organisation's branding resolved by the root layout. */
export function BrandingProvider({ branding, children }: { branding: ResolvedBranding; children: ReactNode }) {
  return <BrandingContext.Provider value={branding}>{children}</BrandingContext.Provider>;
}

export function useBranding(): ResolvedBranding {
  const value = useContext(BrandingContext);
  if (!value) throw new Error("useBranding must be used inside BrandingProvider");
  return value;
}
