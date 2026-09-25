import { useCallback, useEffect, useRef, useState } from "react";

import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { Document } from "@/features/documents/types";

import { chatApi, streamChat } from "../api/chatApi";
import { normalizeAgentStatus } from "../lib/agentStatus";
import { AgentActivity, AgentStatus, ChatMessage, Conversation, GroupEvent } from "../types";

function addMessage(current: ChatMessage[], message: ChatMessage): ChatMessage[] {
  const pendingId = message.sender_type === "assistant" && message.reply_to_message_id ? `pending-${message.reply_to_message_id}` : null;
  const index = current.findIndex((item) => item.id === message.id || item.id === pendingId);
  if (index < 0) return [...current, message];
  // Replace in place so another assistant's ongoing response keeps its position.
  return current.flatMap((item, position) => position === index ? [message] : item.id === message.id || item.id === pendingId ? [] : [item]);
}

function pendingMessage(replyId: string): ChatMessage {
  return { id: `pending-${replyId}`, sender_type: "assistant", sender_id: null, content: "", sources: [], reply_to_message_id: replyId, created_at: new Date().toISOString() };
}

function settlePending(messages: ChatMessage[]) {
  return messages.filter((message) => !message.id.startsWith("pending-") || message.content).map((message) =>
    message.id.startsWith("pending-") ? { ...message, id: message.id.replace("pending-", "interrupted-") } : message
  );
}

export function useChat() {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationDocuments, setConversationDocuments] = useState<Document[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [activities, setActivities] = useState<Record<string, AgentStatus | null>>({});
  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "reconnecting">("connecting");
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamControllerRef = useRef<AbortController | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const sessionRef = useRef(0);
  const mountedRef = useRef(true);
  const sendingRef = useRef(false);
  const latestMessageIdRef = useRef<string | undefined>(undefined);
  const token = useAuthStore((state) => state.token);
  const conversationType = conversation?.type;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      streamControllerRef.current?.abort();
      socketRef.current?.close();
    };
  }, []);

  const reset = useCallback(() => {
    sessionRef.current += 1;
    streamControllerRef.current?.abort();
    streamControllerRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
    sendingRef.current = false;
    latestMessageIdRef.current = undefined;
    setConversation(null);
    setConversationId(null);
    setMessages([]);
    setConversationDocuments([]);
    setError(null);
    setIsSending(false);
    setActivities({});
    setConnectionState("connecting");
    setIsLoadingConversation(false);
    return sessionRef.current;
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    const session = reset();
    setIsLoadingConversation(true);
    try {
      const [detail, documents] = await Promise.all([
        chatApi.getConversation(id),
        chatApi.listDocuments(id).catch(() => [] as Document[]),
      ]);
      if (!mountedRef.current || session !== sessionRef.current) return;
      setConversation(detail);
      setConversationId(detail.id);
      setMessages(detail.messages);
      setConversationDocuments(documents);
      latestMessageIdRef.current = detail.messages.at(-1)?.id;
    } catch (err) {
      if (mountedRef.current && session === sessionRef.current) setError(friendlyErrorMessage(err, "بارگذاری گفتگو ناموفق بود."));
    } finally {
      if (mountedRef.current && session === sessionRef.current) setIsLoadingConversation(false);
    }
  }, [reset]);

  const startNewConversation = useCallback(() => { reset(); }, [reset]);

  useEffect(() => {
    if (!conversationId || !conversationType || !token) return;
    const isGroupConversation = conversationType === "project_group";
    const session = sessionRef.current;
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let socket: WebSocket;
    const active = () => mountedRef.current && !stopped && session === sessionRef.current;
    const receiveMessage = (message: ChatMessage) => {
      latestMessageIdRef.current = message.id;
      if (message.sender_type === "assistant" && message.reply_to_message_id) {
        setActivities((current) => {
          const next = { ...current };
          delete next[message.reply_to_message_id!];
          return next;
        });
      }
      setMessages((current) => addMessage(current, message));
    };
    const connect = () => {
      if (!active()) return;
      try {
        const currentToken = localStorage.getItem("auth_token") ?? token;
        socket = new WebSocket(chatApi.websocketUrl(conversationId, currentToken));
        socketRef.current = socket;
        socket.onopen = async () => {
          if (!active()) return;
          setConnectionState("connected");
          const documentSync = chatApi.listDocuments(conversationId).then((documents) => {
            if (active()) setConversationDocuments(documents);
          }).catch(() => {});
          if (isGroupConversation) {
            try {
              const missed = await chatApi.listMessages(conversationId, latestMessageIdRef.current);
              if (active()) missed.forEach(receiveMessage);
            } catch (err) {
              if (active()) setError(friendlyErrorMessage(err, "همگام‌سازی پیام‌ها ناموفق بود."));
            }
          }
          await documentSync;
        };
        socket.onmessage = (event) => {
          if (!active()) return;
          let payload: GroupEvent;
          try { payload = JSON.parse(event.data) as GroupEvent; } catch { return; }
          if (!payload || typeof payload !== "object") return;
          if (payload.event === "document_status") {
            setConversationDocuments((current) => current.map((document) => document.id === payload.document_id ? { ...document, status: payload.status } : document));
            if (payload.status === "failed") {
              void chatApi.listDocuments(conversationId).then((documents) => {
                if (active()) setConversationDocuments(documents);
              }).catch(() => {});
            }
          } else if (isGroupConversation && payload.event === "message" && payload.message) {
            receiveMessage(payload.message);
          } else if (isGroupConversation && payload.event === "assistant_start") {
            setActivities((current) => ({ ...current, [payload.reply_to_message_id]: { status: "preparing" } }));
            setMessages((current) => current.some((item) => item.id === `pending-${payload.reply_to_message_id}`) ? current : [...current, pendingMessage(payload.reply_to_message_id)]);
          } else if (isGroupConversation && payload.event === "assistant_status") {
            const status = normalizeAgentStatus(payload);
            if (status) setActivities((current) => ({ ...current, [payload.reply_to_message_id]: status }));
          } else if (isGroupConversation && payload.event === "assistant_delta") {
            setActivities((current) => ({ ...current, [payload.reply_to_message_id]: null }));
            setMessages((current) => {
              const pending = pendingMessage(payload.reply_to_message_id);
              return current.some((item) => item.id === pending.id)
                ? current.map((item) => item.id === pending.id ? { ...item, content: item.content + payload.delta } : item)
                : [...current, { ...pending, content: payload.delta }];
            });
          }
        };
        socket.onclose = () => {
          if (!active()) return;
          setConnectionState("reconnecting");
          if (isGroupConversation) {
            setActivities({});
            // Catch-up will restore final messages after reconnection.
            setMessages((current) => current.filter((message) => !message.id.startsWith("pending-")));
          }
          retryTimer = setTimeout(connect, 2500);
        };
      } catch (err) {
        if (active()) {
          setConnectionState("reconnecting");
          setError(friendlyErrorMessage(err, "اتصال گفتگو ناموفق بود."));
          retryTimer = setTimeout(connect, 2500);
        }
      }
    };
    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [conversationId, conversationType, token]);

  const hasProcessingDocuments = conversationDocuments.some((document) => document.status === "processing");

  useEffect(() => {
    if (!conversationId || !hasProcessingDocuments) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const documents = await chatApi.listDocuments(conversationId);
        if (!cancelled) setConversationDocuments(documents);
      } catch {
        // The WebSocket remains the primary channel; polling retries quietly.
      }
      if (!cancelled) timer = setTimeout(poll, 3000);
    };
    timer = setTimeout(poll, 3000);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [conversationId, hasProcessingDocuments]);

  const registerDocument = useCallback((document: Document) => {
    setConversationDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
  }, []);

  const sendMessage = useCallback(async (text: string, linkedProjectId: string | null = null) => {
    if (sendingRef.current || !text.trim() || isLoadingConversation) return;
    const session = sessionRef.current;
    sendingRef.current = true;
    setIsSending(true);
    setError(null);
    if (conversation?.type === "project_group" && conversationId) {
      try {
        const message = await chatApi.postGroupMessage(conversationId, text);
        if (!mountedRef.current || session !== sessionRef.current) return;
        latestMessageIdRef.current = message.id;
        setMessages((current) => addMessage(current, message));
      } catch (err) {
        if (mountedRef.current && session === sessionRef.current) setError(friendlyErrorMessage(err, "ارسال پیام ناموفق بود."));
      } finally {
        if (mountedRef.current && session === sessionRef.current) { sendingRef.current = false; setIsSending(false); }
      }
      return;
    }
    const controller = new AbortController();
    streamControllerRef.current = controller;
    const active = () => mountedRef.current && session === sessionRef.current && !controller.signal.aborted;
    let targetId = conversationId;
    try {
      if (!targetId && linkedProjectId) {
        const created = await chatApi.createPersonal(linkedProjectId);
        if (!active()) return;
        targetId = created.id;
        setConversation(created);
        setConversationId(created.id);
        window.dispatchEvent(new Event("orbit:conversations-changed"));
      }
      const replyId = crypto.randomUUID();
      const userMessage: ChatMessage = { id: `local-${replyId}`, sender_type: "user", sender_id: null, content: text, sources: [], reply_to_message_id: null, created_at: new Date().toISOString() };
      const assistantMessage = { ...pendingMessage(replyId), reply_to_message_id: null };
      setMessages((current) => [...current, userMessage, assistantMessage]);
      setActivities({ [replyId]: { status: "preparing" } });
      await streamChat(text, targetId, {
        onStart: (id) => {
          if (!active()) return;
          targetId = id;
          setConversationId(id);
        },
        onStatus: (status) => { if (active()) setActivities({ [replyId]: status }); },
        onDelta: (delta) => {
          if (!active()) return;
          setActivities({ [replyId]: null });
          setMessages((current) => current.map((item) => item.id === assistantMessage.id ? { ...item, content: item.content + delta } : item));
        },
        onDone: (sources, messageId) => {
          if (!active()) return;
          setActivities({});
          setMessages((current) => current.map((item) => item.id === assistantMessage.id ? { ...item, id: messageId, sources } : item));
          if (targetId) void chatApi.getConversation(targetId).then((detail) => { if (active()) setConversation(detail); }).catch(() => {});
          window.dispatchEvent(new Event("orbit:conversations-changed"));
        },
        onError: (message) => { if (active()) setError(message); },
      }, controller.signal);
    } catch (err) {
      if (active()) setError(friendlyErrorMessage(err, "ارسال پیام ناموفق بود."));
    } finally {
      if (mountedRef.current && session === sessionRef.current && streamControllerRef.current === controller) {
        streamControllerRef.current = null;
        sendingRef.current = false;
        setIsSending(false);
        setActivities({});
        setMessages(settlePending);
      }
    }
  }, [conversation, conversationId, isLoadingConversation]);

  const stopResponse = useCallback(() => {
    streamControllerRef.current?.abort();
    setActivities({});
    setMessages(settlePending);
  }, []);

  const linkProject = useCallback(async (projectId: string | null) => {
    if (!conversationId) return;
    const session = sessionRef.current;
    const updated = await chatApi.linkProject(conversationId, projectId);
    if (mountedRef.current && session === sessionRef.current) setConversation(updated);
    window.dispatchEvent(new Event("orbit:conversations-changed"));
  }, [conversationId]);

  const renameConversation = useCallback(async (title: string) => {
    if (!conversation) return;
    const session = sessionRef.current;
    const updated = await chatApi.renameConversation(conversation, title);
    if (mountedRef.current && session === sessionRef.current) setConversation(updated);
    window.dispatchEvent(new Event("orbit:conversations-changed"));
  }, [conversation]);

  const agentActivities: AgentActivity[] = Object.entries(activities).map(([replyId, status]) => ({ replyId, status }));
  return {
    conversation, conversationId, messages, conversationDocuments, hasProcessingDocuments, isStreaming: isSending || agentActivities.length > 0,
    isSending, agentActivities, connectionState, isLoadingConversation, error,
    sendMessage, loadConversation, startNewConversation, linkProject, renameConversation, stopResponse, registerDocument,
  };
}
