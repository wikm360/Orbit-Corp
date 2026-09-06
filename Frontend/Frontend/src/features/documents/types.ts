export type DocumentStatus = "processing" | "ready" | "failed";

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error_message: string | null;
  team_id: string;
  uploaded_by: string | null;
  created_at: string;
}

export interface TeamOption {
  id: string;
  name: string;
}
