import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  authorizedFetch,
  parseErrorMessage,
} from "@/shared/lib/apiClient";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { Document } from "@/features/documents/types";

import { normalizeAgentStatus } from "../lib/agentStatus";
import { createEventStreamParser } from "../lib/eventStream";

import { AgentStatus, ChatMessage, Conversation, ConversationDetail, SourceCitation } from "../types";

export interface ChatStreamHandlers {
  onStart?: (conversationId: string) => void;
  onStatus?: (status: AgentStatus) => void;
  onDelta: (text: string) => void;
  onDone?: (sources: SourceCitation[], messageId: string) => void;
  onError?: (message: string) => void;
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await authorizedFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal,
    });
    if (!response.ok) throw new ApiError(response.status, await parseErrorMessage(response));
    if (!response.body) throw new Error("پاسخی از سرور دریافت نشد.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let completed = false;
    const parser = createEventStreamParser((eventName, payload) => {
      if (signal?.aborted || completed) return;
      const data = payload as Record<string, unknown>;
      if (eventName === "start" && typeof data.conversation_id === "string") handlers.onStart?.(data.conversation_id);
      else if (eventName === "status") {
        const status = normalizeAgentStatus(data);
        if (status) handlers.onStatus?.(status);
      } else if (eventName === "delta" && typeof data.content === "string") handlers.onDelta(data.content);
      else if (eventName === "done" && typeof data.message_id === "string") {
        completed = true;
        handlers.onDone?.((data.sources ?? []) as SourceCitation[], data.message_id);
      } else if (eventName === "error") {
        throw new Error(typeof data.message === "string" ? data.message : "پاسخ‌گویی با خطا متوقف شد.");
      }
    });
    try {
      while (!completed) {
        const { done, value } = await reader.read();
        if (done) {
          parser.push(decoder.decode());
          parser.finish();
          break;
        }
        parser.push(decoder.decode(value, { stream: true }));
      }
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
    if (!completed) throw new Error("ارتباط با سرور پیش از تکمیل پاسخ قطع شد.");
  } catch (error) {
    if (signal?.aborted || (error instanceof DOMException && error.name === "AbortError")) return;
    handlers.onError?.(friendlyErrorMessage(error, "ارسال پیام ناموفق بود."));
  }
}

export const chatApi = {
  listConversations: () => apiRequest<Conversation[]>("/chat/conversations"),
  getConversation: (id: string) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`),
  createPersonal: (linkedProjectId?: string | null, title?: string) =>
    apiRequest<Conversation>("/chat/conversations", {
      method: "POST",
      body: {
        type: "personal",
        linked_project_id: linkedProjectId || null,
        ...(title ? { title } : {}),
      },
    }),
  createGroup: (projectId: string, title?: string) => apiRequest<Conversation>("/chat/conversations", {
    method: "POST", body: { type: "project_group", project_id: projectId, ...(title?.trim() ? { title: title.trim() } : {}) },
  }),
  linkProject: (id: string, projectId: string | null) => apiRequest<Conversation>(`/chat/conversations/${id}`, {
    method: "PATCH", body: { linked_project_id: projectId },
  }),
  renameConversation: async (conversation: Conversation, title: string) => {
    const updated = await apiRequest<Conversation>(`/chat/conversations/${conversation.id}`, {
      method: "PATCH",
      body: { title: title.trim(), linked_project_id: conversation.type === "personal" ? conversation.linked_project_id : null },
    });
    if (updated.title !== title.trim()) throw new Error("سرور تغییر عنوان را تأیید نکرد. نسخهٔ جدید بک‌اند باید فعال باشد.");
    return updated;
  },
  listMessages: (id: string, after?: string) => apiRequest<ChatMessage[]>(`/chat/conversations/${id}/messages${after ? `?after=${encodeURIComponent(after)}` : ""}`),
  postGroupMessage: (id: string, content: string) => apiRequest<ChatMessage>(`/chat/conversations/${id}/messages`, {
    method: "POST", body: { content },
  }),
  uploadDocument: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>(`/chat/conversations/${id}/documents`, { method: "POST", formData });
  },
  listDocuments: (id: string) => apiRequest<Document[]>(`/chat/conversations/${id}/documents`),
  websocketUrl: (id: string, token: string) => {
    const wsBase = API_BASE_URL.startsWith("https://")
      ? API_BASE_URL.replace("https://", "wss://")
      : API_BASE_URL.replace("http://", "ws://");
    return `${wsBase}/chat/conversations/${id}/ws?token=${encodeURIComponent(token)}`;
  },
};
