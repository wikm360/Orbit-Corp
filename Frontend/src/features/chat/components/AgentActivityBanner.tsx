"use client";

interface AgentActivityBannerProps {
  statusText?: string;
  isStreaming: boolean;
}

export function AgentActivityBanner({ statusText, isStreaming }: AgentActivityBannerProps) {
  if (!isStreaming && !statusText) return null;

  return (
    <div className="mb-2 inline-flex items-center gap-2 rounded-xl border border-brand-100 bg-brand-50/60 px-3 py-1.5 text-xs text-brand-800 transition-all animate-fade-in">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-600" />
      </span>
      <span>{statusText || "هوش مصنوعی در حال تحلیل و آماده‌سازی پاسخ..."}</span>
    </div>
  );
}

