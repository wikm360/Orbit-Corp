export interface SourceCitation {
  document_id: string;
  document_filename: string;
  chunk_index: number;
  snippet: string;
  score: number;
}

export interface ChatMessage {
  id: string;
  sender_type: "user" | "assistant";
  sender_id: string | null;
  content: string;
  sources: SourceCitation[];
  reply_to_message_id: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  type: "personal" | "project_group";
  project_id: string | null;
  linked_project_id: string | null;
  created_by: string | null;
  title: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export type GroupEvent =
  | { event: "message"; message: ChatMessage }
  | { event: "assistant_start"; reply_to_message_id: string }
  | { event: "assistant_status"; reply_to_message_id: string; status: string }
  | { event: "assistant_delta"; reply_to_message_id: string; delta: string };
