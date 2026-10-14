import type { Document } from "@/features/documents/types";

type TerminalStatus = "ready" | "failed";

/** One tracker per conversation session. HTTP snapshots can lag behind uploads and socket events. */
export class ConversationDocumentTracker {
  private documents = new Map<string, Document>();
  private statuses = new Map<string, TerminalStatus>();

  get snapshot(): Document[] {
    return [...this.documents.values()];
  }

  get hasProcessing(): boolean {
    return this.snapshot.some((document) => document.status === "processing");
  }

  merge(incoming: Document[]): Document[] {
    for (const document of incoming) {
      const previous = this.documents.get(document.id);
      // A terminal event can arrive before the POST response. Also retain terminal
      // HTTP results when an older request subsequently returns "processing".
      const status = this.statuses.get(document.id)
        ?? (document.status === "processing" ? previous?.status : undefined)
        ?? document.status;
      this.documents.set(document.id, {
        ...document,
        status,
        error_message: status === "failed" ? document.error_message ?? previous?.error_message ?? null : null,
      });
    }
    // Keep uploads missing from snapshots taken before they were accepted.
    return this.snapshot;
  }

  receive(payload: unknown): boolean {
    if (!payload || typeof payload !== "object") return false;
    const event = payload as Record<string, unknown>;
    if (event.event !== "document_status" || typeof event.document_id !== "string"
      || (event.status !== "ready" && event.status !== "failed")) return false;
    this.statuses.set(event.document_id, event.status);
    const document = this.documents.get(event.document_id);
    if (document) this.merge([document]);
    return true;
  }
}
