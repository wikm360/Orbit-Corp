import type { Metadata } from "next";
import localFont from "next/font/local";

import { BrandingProvider } from "@/features/branding/BrandingProvider";
import { brandingCss, getBranding } from "@/shared/lib/branding";
import "./globals.css";

// Fallback for B Nazanin (see globals.css). Self-hosted (OFL licence) so the
// app never depends on Google Fonts — which is unreliable from inside Iran.
const vazirmatn = localFont({
  src: "../../public/fonts/Vazirmatn-Variable.woff2",
  weight: "100 900",
  variable: "--font-vazirmatn",
  display: "swap",
});

// Title, description and favicon come from the organisation's branding (set by a super admin in the admin panel).
export async function generateMetadata(): Promise<Metadata> {
  const branding = await getBranding();
  return {
    title: branding.app_title,
    description: branding.description,
    icons: branding.logo_url ? { icon: branding.logo_url } : undefined,
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const branding = await getBranding();
  const css = brandingCss(branding.palette);
  return (
    <html lang="fa" dir="rtl" className={vazirmatn.variable} data-brand={css ? "" : undefined}>
      <head>{css && <style dangerouslySetInnerHTML={{ __html: css }} />}</head>
      <body className="bg-gray-50 text-gray-900">
        <BrandingProvider branding={branding}>{children}</BrandingProvider>
      </body>
    </html>
  );
}
