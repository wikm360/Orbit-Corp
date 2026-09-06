import { useCallback, useEffect, useState } from "react";

import { documentsApi } from "../api/documentsApi";
import { Document } from "../types";

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      setDocuments(await documentsApi.list());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const upload = useCallback(
    async (teamId: string, file: File) => {
      await documentsApi.upload(teamId, file);
      await refresh();
    },
    [refresh]
  );

  const remove = useCallback(
    async (documentId: string) => {
      await documentsApi.remove(documentId);
      await refresh();
    },
    [refresh]
  );

  return { documents, isLoading, error, refresh, upload, remove };
}
