"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { ChatWindow } from "../components/ChatWindow";
import { useChat } from "../hooks/useChat";

export function ChatScreen() {
  const {
    conversationId,
    messages,
    isStreaming,
    isLoadingConversation,
    error,
    sendMessage,
    loadConversation,
    startNewConversation,
  } = useChat();
  const searchParams = useSearchParams();
  const lastRouteAction = useRef<string | null>(null);
  const selectedConversationId = searchParams.get("conversation");
  const newConversationKey = searchParams.get("new");

  useEffect(() => {
    const routeAction = selectedConversationId
      ? `conversation:${selectedConversationId}`
      : newConversationKey
        ? `new:${newConversationKey}`
        : "empty";

    if (lastRouteAction.current === routeAction) return;
    lastRouteAction.current = routeAction;

    if (selectedConversationId) {
      void loadConversation(selectedConversationId);
    } else {
      startNewConversation();
    }
  }, [loadConversation, newConversationKey, selectedConversationId, startNewConversation]);

  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-white">
      <div className="hidden h-14 shrink-0 items-center justify-between px-5 md:flex">
        <button type="button" className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 transition hover:bg-gray-100">
          دستیار اسناد سازمان
          <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4 text-gray-500">
            <path strokeLinecap="round" strokeLinejoin="round" d="m6 8 4 4 4-4" />
          </svg>
        </button>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          متصل به دانش سازمان
        </div>
      </div>
      <div className="min-h-0 flex-1">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          isLoadingConversation={isLoadingConversation}
          error={error}
          onSend={sendMessage}
        />
      </div>
      <span className="sr-only" aria-live="polite">{conversationId ? "گفتگو انتخاب شده است" : "گفتگوی جدید"}</span>
    </main>
  );
}
