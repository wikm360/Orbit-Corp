import { API_BASE_URL, apiRequest } from "@/shared/lib/apiClient";

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
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken() ?? ""}`,
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  });

  if (!response.ok || !response.body) {
    handlers.onError?.(`Request failed with status ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event: "));
      const dataLine = lines.find((l) => l.startsWith("data: "));
      if (!eventLine || !dataLine) continue;

      const eventName = eventLine.replace("event: ", "").trim();
      const data = JSON.parse(dataLine.replace("data: ", ""));

      if (eventName === "start") handlers.onStart?.(data.conversation_id);
      else if (eventName === "delta") handlers.onDelta(data.content);
      else if (eventName === "done") handlers.onDone?.(data.sources, data.message_id);
    }
  }
}

export const chatApi = {
  listConversations: () => apiRequest<Conversation[]>("/chat/conversations"),
  getConversation: (id: string) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`),
};
