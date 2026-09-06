import { useCallback, useState } from "react";

import { chatApi, streamChat } from "../api/chatApi";
import { ChatMessage } from "../types";

export function useChat(initialConversationId: string | null = null) {
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConversation = useCallback(async (id: string) => {
    const detail = await chatApi.getConversation(id);
    setConversationId(detail.id);
    setMessages(detail.messages);
  }, []);

  const startNewConversation = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      const userMessage: ChatMessage = {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        sources: [],
      };
      const assistantMessage: ChatMessage = {
        id: `pending-${Date.now()}`,
        role: "assistant",
        content: "",
        sources: [],
      };
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      await streamChat(text, conversationId, {
        onStart: (id) => setConversationId(id),
        onDelta: (delta) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next.at(-1);
            if (!last) return prev;
            next[next.length - 1] = { ...last, content: last.content + delta };
            return next;
          });
        },
        onDone: (sources) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next.at(-1);
            if (!last) return prev;
            next[next.length - 1] = { ...last, sources };
            return next;
          });
          setIsStreaming(false);
        },
        onError: (message) => {
          setError(message);
          setIsStreaming(false);
        },
      });
    },
    [conversationId]
  );

  return {
    conversationId,
    messages,
    isStreaming,
    error,
    sendMessage,
    loadConversation,
    startNewConversation,
  };
}
