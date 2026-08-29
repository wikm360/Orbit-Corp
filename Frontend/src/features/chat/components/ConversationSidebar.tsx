"use client";

import { useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { chatApi } from "../api/chatApi";
import { Conversation } from "../types";

interface ConversationSidebarProps {
  activeConversationId: string | null;
  onSelect: (id: string) => void;
  onNewConversation: () => void;
}

export function ConversationSidebar({
  activeConversationId,
  onSelect,
  onNewConversation,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    chatApi.listConversations().then(setConversations).catch(() => setConversations([]));
  }, [activeConversationId]);

  return (
    <aside className="flex w-64 flex-col border-l border-gray-200 bg-gray-50">
      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="w-full rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-white"
        >
          + گفتگوی جدید
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={cn(
              "mb-1 w-full truncate rounded-md px-3 py-2 text-right text-sm hover:bg-white",
              conversation.id === activeConversationId && "bg-white font-medium"
            )}
          >
            {conversation.title}
          </button>
        ))}
      </div>
    </aside>
  );
}
