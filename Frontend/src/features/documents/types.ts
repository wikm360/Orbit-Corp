export type DocumentStatus = "processing" | "ready" | "failed" | "cancelled" | "unsupported";

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error_message: string | null;
  project_id: string | null;
  conversation_id: string | null;
  /** File-manager location inside the project (null = project root). Absent on conversation documents. */
  folder_id?: string | null;
  uploaded_by: string | null;
  created_at: string;
}

export type ArchiveImportStatus = "extracting" | "done" | "failed";

/** An uploaded .zip/.rar/.7z the worker is unpacking into `folder_id` (null = project root). */
export interface ArchiveImport {
  id: string;
  folder_id: string | null;
  filename: string;
  status: ArchiveImportStatus;
  error_message: string | null;
  total_files: number;
  imported_files: number;
  skipped_files: number;
  failed_files: { path: string; error: string }[];
  created_at: string;
  finished_at: string | null;
}

export type BatchUploadItem =
  | { filename: string; status: "accepted"; document: Document | null; archive?: ArchiveImport | null; error: null }
  | { filename: string; status: "rejected"; document: null; archive?: null; error: string };

export interface BatchUploadResponse {
  accepted: number;
  rejected: number;
  items: BatchUploadItem[];
}

export interface Folder {
  id: string;
  parent_id: string | null;
  name: string;
  created_at: string;
}

/** Documents by status over a folder and everything below it; statuses with no documents are absent. */
export type StatusCounts = Partial<Record<DocumentStatus, number>>;

export interface FolderEntry {
  folder: Folder;
  status_counts: StatusCounts;
}

export interface FolderListing {
  folder_id: string | null;
  breadcrumb: Folder[];
  folders: FolderEntry[];
  documents: Document[];
  archives: ArchiveImport[];
}

export interface DocumentSearchHit {
  document: Document;
  path: string[];
}

/** What a file manager has selected; folders include everything inside them. */
export interface FileSelection {
  document_ids: string[];
  folder_ids: string[];
}

/** `fail` answers 409 without changing anything when a name is taken; `rename` keeps both (`name (1)`). */
export type OnConflict = "fail" | "rename";

export interface BulkResult {
  count: number;
  skipped: number;
}
