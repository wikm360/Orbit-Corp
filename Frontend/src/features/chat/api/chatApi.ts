import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  notifyUnauthorized,
  parseErrorMessage,
} from "@/shared/lib/apiClient";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { Conversation, ConversationDetail, SourceCitation } from "../types";

export interface ChatStreamHandlers {
  onStart?: (conversationId: string) => void;
  onDelta: (text: string) => void;
  onDone?: (sources: SourceCitation[], messageId: string) => void;
  onError?: (message: string) => void;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

/** Parses the backend's `text/event-stream` response (SSE) line by line. */
export async function streamChat(
  message: string,
  conversationId: string | null,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken() ?? ""}`,
      },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) notifyUnauthorized();
      throw new ApiError(response.status, await parseErrorMessage(response));
    }
    if (!response.body) throw new Error("پاسخی از سرور دریافت نشد.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completed = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        const lines = rawEvent.split("\n");
        const eventLine = lines.find((line) => line.startsWith("event:"));
        const dataLines = lines
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart());
        if (!eventLine || dataLines.length === 0) continue;

        const eventName = eventLine.slice(6).trim();
        const data = JSON.parse(dataLines.join("\n"));

        if (eventName === "start") handlers.onStart?.(data.conversation_id);
        else if (eventName === "delta") handlers.onDelta(data.content);
        else if (eventName === "done") {
          completed = true;
          handlers.onDone?.(data.sources ?? [], data.message_id);
        } else if (eventName === "error") {
          throw new Error(data.message ?? "پاسخ‌گویی با خطا متوقف شد.");
        }
      }
    }

    if (!completed) throw new Error("ارتباط با سرور پیش از تکمیل پاسخ قطع شد.");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    handlers.onError?.(friendlyErrorMessage(error, "ارسال پیام ناموفق بود."));
  }
}

export const chatApi = {
  listConversations: () => apiRequest<Conversation[]>("/chat/conversations"),
  getConversation: (id: string) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`),
};
