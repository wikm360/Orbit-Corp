export type DocumentStatus = "processing" | "ready" | "failed";

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error_message: string | null;
  project_id: string | null;
  conversation_id: string | null;
  uploaded_by: string | null;
  created_at: string;
}
