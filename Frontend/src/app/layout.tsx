import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

// Fallback for B Nazanin (see globals.css). Self-hosted (OFL licence) so the
// app never depends on Google Fonts — which is unreliable from inside Iran.
const vazirmatn = localFont({
  src: "../../public/fonts/Vazirmatn-Variable.woff2",
  weight: "100 900",
  variable: "--font-vazirmatn",
  display: "swap",
});

export const metadata: Metadata = {
  title: "دستیار هوشمند محور گستر",
  description: "دستیار داخلی شرکت محور گستر نصر، متصل به اسناد و قراردادهای سازمان",
  icons: { icon: "/logo.jpg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl" className={vazirmatn.variable}>
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
