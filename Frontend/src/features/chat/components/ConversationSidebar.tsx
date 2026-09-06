"use client";

import { useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { chatApi } from "../api/chatApi";
import { Conversation } from "../types";

interface ConversationSidebarProps {
  activeConversationId: string | null;
  onSelect: (id: string) => void;
  onNewConversation: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export function ConversationSidebar({
  activeConversationId,
  onSelect,
  onNewConversation,
  isOpen,
  onClose,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    chatApi
      .listConversations()
      .then((items) => {
        if (!cancelled) {
          setConversations(items);
          setHasError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setHasError(true);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeConversationId]);

  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="بستن تاریخچه گفتگوها"
          className="fixed inset-0 z-30 bg-brand-900/25 backdrop-blur-[1px] md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        aria-label="تاریخچه گفتگوها"
        className={`fixed inset-y-0 right-0 z-40 flex w-72 shrink-0 flex-col border-l border-gray-200 bg-gray-50 shadow-2xl transition-transform duration-200 md:relative md:z-auto md:translate-x-0 md:shadow-none ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2 border-b border-gray-200 p-3">
        <button
          type="button"
          onClick={() => {
            onNewConversation();
            onClose();
          }}
          className="flex-1 rounded-xl border border-dashed border-brand-300 bg-white px-3 py-2.5 text-sm font-medium text-brand-700 transition hover:bg-brand-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-100"
        >
          + گفتگوی جدید
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-200 md:hidden"
          aria-label="بستن"
        >
          ×
        </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
        {isLoading && <p className="px-3 py-4 text-xs text-gray-400">در حال دریافت گفتگوها...</p>}
        {!isLoading && hasError && (
          <p className="rounded-xl bg-red-50 px-3 py-3 text-xs leading-5 text-red-700">
            دریافت تاریخچه گفتگوها ناموفق بود.
          </p>
        )}
        {!isLoading && !hasError && conversations.length === 0 && (
          <p className="px-3 py-4 text-xs leading-6 text-gray-400">هنوز گفتگویی ذخیره نشده است.</p>
        )}
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            onClick={() => {
              onSelect(conversation.id);
              onClose();
            }}
            className={cn(
              "mb-1 w-full truncate rounded-xl px-3 py-2.5 text-right text-sm text-gray-600 transition hover:bg-white hover:text-gray-900 focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-100",
              conversation.id === activeConversationId &&
                "bg-white font-semibold text-brand-700 shadow-sm"
            )}
          >
            {conversation.title}
          </button>
        ))}
        </div>
      </aside>
    </>
  );
}
