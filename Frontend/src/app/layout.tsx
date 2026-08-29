import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "دستیار هوشمند سازمانی",
  description: "چت‌بات داخلی سازمان متصل به اسناد داخلی",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
