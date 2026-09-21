import { useCallback, useEffect, useRef, useState } from "react";

import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";

import { chatApi, streamChat } from "../api/chatApi";
import { ChatMessage, Conversation, GroupEvent } from "../types";

function addMessage(current: ChatMessage[], message: ChatMessage): ChatMessage[] {
  const withoutPending = message.reply_to_message_id
    ? current.filter((item) => item.id !== `pending-${message.reply_to_message_id}`)
    : current;
  const index = withoutPending.findIndex((item) => item.id === message.id);
  if (index < 0) return [...withoutPending, message];
  return withoutPending.map((item, position) => position === index ? message : item);
}

export function useChat() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamControllerRef = useRef<AbortController | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const loadRequestRef = useRef(0);
  const latestMessageIdRef = useRef<string | undefined>(undefined);
  const activeConversationIdRef = useRef<string | null>(null);
  const token = useAuthStore((state) => state.token);

  useEffect(() => () => {
    streamControllerRef.current?.abort();
    socketRef.current?.close();
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    streamControllerRef.current?.abort();
    socketRef.current?.close();
    setIsStreaming(false);
    setError(null);
    setIsLoadingConversation(true);
    const requestId = ++loadRequestRef.current;
    try {
      const detail = await chatApi.getConversation(id);
      if (requestId !== loadRequestRef.current) return;
      setConversation(detail);
      setConversationId(detail.id);
      setMessages(detail.messages);
      latestMessageIdRef.current = detail.messages.at(-1)?.id;
    } catch (err) {
      if (requestId === loadRequestRef.current) setError(friendlyErrorMessage(err, "بارگذاری گفتگو ناموفق بود."));
    } finally {
      if (requestId === loadRequestRef.current) setIsLoadingConversation(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
    streamControllerRef.current?.abort();
    socketRef.current?.close();
    loadRequestRef.current += 1;
    latestMessageIdRef.current = undefined;
    activeConversationIdRef.current = null;
    setConversation(null);
    setConversationId(null);
    setMessages([]);
    setError(null);
    setIsStreaming(false);
    setIsLoadingConversation(false);
  }, []);

  useEffect(() => {
    if (!conversationId || conversation?.type !== "project_group" || !token) return;
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let socket: WebSocket;
    const connect = async () => {
      try {
        // A REST request refreshes an expired access token before the WS handshake.
        await chatApi.listMessages(conversationId, latestMessageIdRef.current);
        if (stopped) return;
        const currentToken = localStorage.getItem("auth_token") ?? token;
        socket = new WebSocket(chatApi.websocketUrl(conversationId, currentToken));
        socketRef.current = socket;
        socket.onopen = async () => {
          try {
            const missed = await chatApi.listMessages(conversationId, latestMessageIdRef.current);
            if (stopped) return;
            missed.forEach((message) => {
              latestMessageIdRef.current = message.id;
              setMessages((current) => addMessage(current, message));
            });
          } catch (err) {
            setError(friendlyErrorMessage(err, "همگام‌سازی پیام‌ها ناموفق بود."));
          }
        };
        socket.onmessage = (event) => {
          const payload = JSON.parse(event.data) as GroupEvent;
          if (payload.event === "message") {
            latestMessageIdRef.current = payload.message.id;
            setMessages((current) => addMessage(current, payload.message));
          } else if (payload.event === "assistant_start") {
            setMessages((current) => addMessage(current, {
              id: `pending-${payload.reply_to_message_id}`, sender_type: "assistant", sender_id: null,
              content: "", sources: [], reply_to_message_id: payload.reply_to_message_id, created_at: new Date().toISOString(),
            }));
          } else if (payload.event === "assistant_delta") {
            setMessages((current) => current.map((item) => item.id === `pending-${payload.reply_to_message_id}` ? { ...item, content: item.content + payload.delta } : item));
          }
        };
        socket.onclose = () => {
          if (!stopped) retryTimer = setTimeout(() => void connect(), 2500);
        };
      } catch (err) {
        if (!stopped) {
          setError(friendlyErrorMessage(err, "اتصال گفتگوی گروهی ناموفق بود."));
          retryTimer = setTimeout(() => void connect(), 2500);
        }
      }
    };
    void connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [conversationId, conversation?.type, token]);

  const sendMessage = useCallback(async (text: string, linkedProjectId: string | null = null) => {
    setError(null);
    if (conversation?.type === "project_group" && conversationId) {
      setIsStreaming(true);
      try {
        const message = await chatApi.postGroupMessage(conversationId, text);
        latestMessageIdRef.current = message.id;
        setMessages((current) => addMessage(current, message));
      } catch (err) {
        setError(friendlyErrorMessage(err, "ارسال پیام ناموفق بود."));
      } finally {
        setIsStreaming(false);
      }
      return;
    }
    let targetConversationId = conversationId;
    setIsStreaming(true);
    if (!targetConversationId && linkedProjectId) {
      try {
        const created = await chatApi.createPersonal(linkedProjectId);
        targetConversationId = created.id;
        setConversation(created);
        setConversationId(created.id);
        window.dispatchEvent(new Event("orbit:conversations-changed"));
      } catch (err) {
        setError(friendlyErrorMessage(err, "ایجاد گفتگو ناموفق بود."));
        setIsStreaming(false);
        return;
      }
    }
    const controller = new AbortController();
    streamControllerRef.current?.abort();
    streamControllerRef.current = controller;
    const requestKey = crypto.randomUUID();
    const userMessage: ChatMessage = {
      id: `local-${requestKey}`, sender_type: "user", sender_id: null,
      content: text, sources: [], reply_to_message_id: null, created_at: new Date().toISOString(),
    };
    const assistantMessage: ChatMessage = {
      id: `pending-${requestKey}`, sender_type: "assistant", sender_id: null,
      content: "", sources: [], reply_to_message_id: null, created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);
    await streamChat(text, targetConversationId, {
      onStart: (id) => { activeConversationIdRef.current = id; setConversationId(id); },
      onDelta: (delta) => setMessages((current) => current.map((item) => item.id === assistantMessage.id ? { ...item, content: item.content + delta } : item)),
      onDone: (sources, messageId) => {
        setMessages((current) => current.map((item) => item.id === assistantMessage.id ? { ...item, id: messageId, sources } : item));
        if (activeConversationIdRef.current) void chatApi.getConversation(activeConversationIdRef.current).then(setConversation).catch(() => {});
        window.dispatchEvent(new Event("orbit:conversations-changed"));
      },
      onError: (message) => setError(message),
    }, controller.signal);
    if (streamControllerRef.current === controller) {
      streamControllerRef.current = null;
      setIsStreaming(false);
    }
  }, [conversation, conversationId]);

  const linkProject = useCallback(async (projectId: string | null) => {
    if (!conversationId) return;
    const updated = await chatApi.linkProject(conversationId, projectId);
    setConversation(updated);
  }, [conversationId]);

  return {
    conversation, conversationId, messages, isStreaming, isLoadingConversation, error,
    sendMessage, loadConversation, startNewConversation, linkProject,
  };
}
