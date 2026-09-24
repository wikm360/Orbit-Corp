import { useCallback, useEffect, useRef, useState } from "react";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { documentsApi } from "../api/documentsApi";
import { Document } from "../types";

export function useDocuments(projectId: string | null) {
  const [result, setResult] = useState<{ projectId: string; documents: Document[] } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const documents = result?.projectId === projectId ? result.documents : [];

  const refresh = useCallback(async () => {
    if (!projectId) {
      requestIdRef.current += 1;
      return;
    }
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    try {
      const items = await documentsApi.list(projectId);
      if (requestId === requestIdRef.current) {
        setResult({ projectId, documents: items });
        setError(null);
      }
    } catch (err) {
      if (requestId === requestIdRef.current) setError(friendlyErrorMessage(err, "دریافت فهرست اسناد ناموفق بود."));
    } finally {
      if (requestId === requestIdRef.current) setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    const hasProcessing = documents.some((doc) => doc.status === "processing");
    if (!hasProcessing || !projectId) return;
    const interval = setInterval(async () => {
      try {
        const items = await documentsApi.list(projectId);
        setResult((current) => current?.projectId === projectId ? { projectId, documents: items } : current);
      } catch {
        // Silent catch for background poll
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [documents, projectId]);

  const upload = useCallback(async (file: File) => {
    if (!projectId) return;
    setError(null);
    try {
      await documentsApi.upload(projectId, file);
      await refresh();
    } catch (err) {
      setError(friendlyErrorMessage(err, "آپلود سند ناموفق بود."));
      throw err;
    }
  }, [projectId, refresh]);

  const remove = useCallback(async (documentId: string) => {
    if (!projectId) return;
    setDeletingId(documentId);
    setError(null);
    try {
      await documentsApi.remove(projectId, documentId);
      setResult((current) => current?.projectId === projectId ? { projectId, documents: current.documents.filter((document) => document.id !== documentId) } : current);
    } catch (err) {
      setError(friendlyErrorMessage(err, "حذف سند ناموفق بود."));
      throw err;
    } finally {
      setDeletingId(null);
    }
  }, [projectId]);

  return { documents, isLoading, error, deletingId, refresh, upload, remove };
}
