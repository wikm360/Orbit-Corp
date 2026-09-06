import { useCallback, useEffect, useState } from "react";

import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { documentsApi } from "../api/documentsApi";
import { Document } from "../types";

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      setDocuments(await documentsApi.list());
      setError(null);
    } catch (err) {
      setError(friendlyErrorMessage(err, "دریافت فهرست اسناد ناموفق بود."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    documentsApi
      .list()
      .then((items) => {
        if (!cancelled) {
          setDocuments(items);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(friendlyErrorMessage(err, "دریافت فهرست اسناد ناموفق بود."));
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const upload = useCallback(
    async (teamId: string, file: File) => {
      setError(null);
      try {
        await documentsApi.upload(teamId, file);
        await refresh();
      } catch (err) {
        setError(friendlyErrorMessage(err, "آپلود سند ناموفق بود."));
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
        await documentsApi.remove(documentId);
        setDocuments((current) => current.filter((document) => document.id !== documentId));
      } catch (err) {
        setError(friendlyErrorMessage(err, "حذف سند ناموفق بود."));
        throw err;
      } finally {
        setDeletingId(null);
      }
    },
    []
  );

  return { documents, isLoading, error, deletingId, refresh, upload, remove };
}
