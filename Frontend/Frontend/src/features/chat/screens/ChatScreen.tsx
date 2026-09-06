"use client";

import { useCallback } from "react";

import { ChatWindow } from "../components/ChatWindow";
import { ConversationSidebar } from "../components/ConversationSidebar";
import { useChat } from "../hooks/useChat";

export function ChatScreen() {
  const {
    conversationId,
    messages,
    isStreaming,
    error,
    sendMessage,
    loadConversation,
    startNewConversation,
  } = useChat();

  const handleSelect = useCallback(
    (id: string) => {
      loadConversation(id);
    },
    [loadConversation]
  );

  return (
    <div className="flex h-[calc(100vh-56px)]">
      <div className="flex-1">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          error={error}
          onSend={sendMessage}
        />
      </div>
      <ConversationSidebar
        activeConversationId={conversationId}
        onSelect={handleSelect}
        onNewConversation={startNewConversation}
      />
    </div>
  );
}
