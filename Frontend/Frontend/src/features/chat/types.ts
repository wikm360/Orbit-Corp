export interface SourceCitation {
  document_id: string;
  document_filename: string;
  chunk_index: number;
  snippet: string;
  score: number;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources: SourceCitation[];
  created_at?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}
