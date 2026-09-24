import { useCallback, useEffect, useState } from "react";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { documentsApi } from "../api/documentsApi";
import { Document } from "../types";

export function usePersonalDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const items = await documentsApi.listPersonal();
      setDocuments(items);
      setError(null);
    } catch (err) {
      setError(friendlyErrorMessage(err, "دریافت فهرست اسناد شخصی ناموفق بود."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upload = useCallback(
    async (file: File) => {
      setError(null);
      try {
        await documentsApi.uploadPersonal(file);
        await refresh();
      } catch (err) {
        setError(friendlyErrorMessage(err, "آپلود سند شخصی ناموفق بود."));
        throw err;
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (documentId: string) => {
      setDeletingId(documentId);
      setError(null);
      try {
        await documentsApi.removePersonal(documentId);
        setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      } catch (err) {
        setError(friendlyErrorMessage(err, "حذف سند شخصی ناموفق بود."));
        throw err;
      } finally {
        setDeletingId(null);
      }
    },
    []
  );

  return { documents, isLoading, error, deletingId, refresh, upload, remove };
}

