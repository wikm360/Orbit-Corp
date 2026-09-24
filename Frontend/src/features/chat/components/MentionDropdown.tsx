"use client";

import { useEffect, useRef } from "react";

export interface MentionItem {
  id: string;
  label: string;
  type: "bot" | "personal_doc" | "project_doc";
  subtitle?: string;
}

interface MentionDropdownProps {
  items: MentionItem[];
  selectedIndex: number;
  onSelect: (item: MentionItem) => void;
  onClose: () => void;
}

export function MentionDropdown({
  items,
  selectedIndex,
  onSelect,
  onClose,
}: MentionDropdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  if (items.length === 0) return null;

  return (
    <div
      ref={containerRef}
      role="listbox"
      aria-label="پیشنهادات منشن"
      className="absolute bottom-full mb-2 right-4 z-50 max-h-60 w-72 overflow-y-auto rounded-2xl border border-gray-200 bg-white p-1.5 shadow-xl transition-all animate-fade-up"
    >
      <div className="px-2 py-1 text-[11px] font-semibold text-gray-400">
        منشن بات یا سند موردنظر:
      </div>
      {items.map((item, index) => {
        const isSelected = index === selectedIndex;
        return (
          <button
            key={`${item.type}-${item.id}`}
            type="button"
            role="option"
            aria-selected={isSelected}
            onClick={() => onSelect(item)}
            className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-right transition ${
              isSelected ? "bg-gray-100 text-gray-900 font-medium" : "text-gray-700 hover:bg-gray-50"
            }`}
          >
            {item.type === "bot" ? (
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700">
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                  <path d="M12 2.75 14.1 9.9 21.25 12l-7.15 2.1L12 21.25 9.9 14.1 2.75 12 9.9 9.9 12 2.75Z" />
                </svg>
              </div>
            ) : item.type === "personal_doc" ? (
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6M8 13h8M8 17h6" />
                </svg>
              </div>
            ) : (
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-700">
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18M9 9v12" />
                </svg>
              </div>
            )}

            <div className="min-w-0 flex-1">
              <p className="truncate text-xs">{item.label}</p>
              {item.subtitle && (
                <p className="truncate text-[10px] text-gray-400">{item.subtitle}</p>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

