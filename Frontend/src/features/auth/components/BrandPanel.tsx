"use client";

import { BrandLogo } from "@/features/branding/BrandLogo";
import { useBranding } from "@/features/branding/BrandingProvider";

const HIGHLIGHTS = [
  { title: "پاسخ از دل اسناد", text: "قراردادها، دستورالعمل‌ها و مدارک پروژه‌ها را می‌خواند و جواب دقیق می‌دهد." },
  { title: "منبع هر پاسخ مشخص است", text: "کنار هر جواب می‌بینی از کدام سند و کدام بخش آمده." },
  { title: "فقط اسناد تیم خودت", text: "هر همکار فقط به مدارک تیم‌ها و پروژه‌های خودش دسترسی دارد." },
];

/**
 * The branded half of the auth screens. Deep-blue ground with the two logo
 * colours (yellow / teal) as soft "peaks" echoing the mountain mark.
 */
export function BrandPanel() {
  const branding = useBranding();
  return (
    <section className="relative hidden overflow-hidden bg-brand-800 text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
      {/* decorative peaks */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -start-24 top-1/3 h-[28rem] w-[28rem] rounded-full bg-accent-500/25 blur-3xl animate-float" />
        <div className="absolute -end-32 -bottom-24 h-[30rem] w-[30rem] rounded-full bg-teal-400/25 blur-3xl" />
        <svg
          className="absolute inset-x-0 bottom-0 w-full opacity-[0.12]"
          viewBox="0 0 800 260"
          fill="none"
          preserveAspectRatio="none"
        >
          <path d="M0 260 L220 40 L400 200 L560 20 L800 260 Z" className="fill-accent-500" />
          <path d="M120 260 L380 60 L520 190 L700 40 L800 260 Z" className="fill-teal-400" />
        </svg>
      </div>

      <div className="relative">
        <div className="inline-flex items-center gap-4 rounded-2xl bg-white/95 p-3 pe-5 shadow-card">
          <BrandLogo className="h-16 w-16" rounded="rounded-lg" />
          <div className="text-brand-800">
            <p className="text-lg font-bold leading-tight">{branding.name}</p>
            <p className="text-sm text-brand-500">{branding.tagline}</p>
          </div>
        </div>
      </div>

      <div className="relative max-w-md">
        <h2 className="text-balance text-3xl font-bold leading-snug">
          {branding.login_headline}
        </h2>
        <ul className="mt-8 space-y-5">
          {HIGHLIGHTS.map((item, index) => (
            <li key={item.title} className="flex gap-4">
              <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-500 text-sm font-bold text-brand-900">
                {["۱", "۲", "۳"][index]}
              </span>
              <div>
                <p className="font-bold">{item.title}</p>
                <p className="mt-0.5 text-sm leading-relaxed text-brand-100/90">{item.text}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <p className="relative text-xs text-brand-200/80">
        {branding.login_footer}
      </p>
    </section>
  );
}
