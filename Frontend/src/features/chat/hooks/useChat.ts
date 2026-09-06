import { useCallback, useEffect, useRef, useState } from "react";

import { chatApi, streamChat } from "../api/chatApi";
import { ChatMessage } from "../types";

export function useChat(initialConversationId: string | null = null) {
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamControllerRef = useRef<AbortController | null>(null);
  const loadRequestRef = useRef(0);

  useEffect(() => () => streamControllerRef.current?.abort(), []);

  const loadConversation = useCallback(async (id: string) => {
    streamControllerRef.current?.abort();
    setIsStreaming(false);
    setError(null);
    setIsLoadingConversation(true);
    const requestId = ++loadRequestRef.current;
    try {
      const detail = await chatApi.getConversation(id);
      if (requestId !== loadRequestRef.current) return;
      setConversationId(detail.id);
      setMessages(detail.messages);
    } catch {
      if (requestId === loadRequestRef.current) {
        setError("بارگذاری این گفتگو ناموفق بود. دوباره تلاش کنید.");
      }
    } finally {
      if (requestId === loadRequestRef.current) setIsLoadingConversation(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
    streamControllerRef.current?.abort();
    loadRequestRef.current += 1;
    setConversationId(null);
    setMessages([]);
    setError(null);
    setIsStreaming(false);
    setIsLoadingConversation(false);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      const controller = new AbortController();
      streamControllerRef.current?.abort();
      streamControllerRef.current = controller;
      const requestKey = Date.now();
      const userMessage: ChatMessage = {
        id: `local-${requestKey}`,
        role: "user",
        content: text,
        sources: [],
      };
      const assistantMessage: ChatMessage = {
        id: `pending-${requestKey}`,
        role: "assistant",
        content: "",
        sources: [],
      };
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      await streamChat(text, conversationId, {
        onStart: (id) => setConversationId(id),
        onDelta: (delta) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? { ...item, content: item.content + delta }
                : item
            )
          );
        },
        onDone: (sources, messageId) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id ? { ...item, id: messageId, sources } : item
            )
          );
          window.dispatchEvent(new Event("orbit:conversations-changed"));
        },
        onError: (message) => {
          setError(message);
        },
      }, controller.signal);
      if (streamControllerRef.current === controller) {
        streamControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [conversationId]
  );

  return {
    conversationId,
    messages,
    isStreaming,
    isLoadingConversation,
    error,
    sendMessage,
    loadConversation,
    startNewConversation,
  };
}
