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

export type BatchUploadItem =
  | { filename: string; status: "accepted"; document: Document; error: null }
  | { filename: string; status: "rejected"; document: null; error: string };

export interface BatchUploadResponse {
  accepted: number;
  rejected: number;
  items: BatchUploadItem[];
}
