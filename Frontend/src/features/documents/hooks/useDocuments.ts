import { useCallback, useEffect, useRef, useState } from "react";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { documentsApi } from "../api/documentsApi";
import { uploadFileBatches } from "../lib/batchUpload";
import type { BatchUploadHandler } from "./useBatchUpload";
import type { Document } from "../types";

const EMPTY_DOCUMENTS: Document[] = [];

export function useDocuments(projectId: string | null) {
  const [result, setResult] = useState<{ projectId: string; documents: Document[] } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorState, setError] = useState<{ projectId: string; message: string } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingIds, setRetryingIds] = useState<string[]>([]);
  const sessionRef = useRef(0);
  const requestRef = useRef(0);
  const mutationRef = useRef(0);
  const retryingRef = useRef(new Set<string>());
  const documents = result?.projectId === projectId ? result.documents : EMPTY_DOCUMENTS;
  const error = errorState?.projectId === projectId ? errorState.message : null;

  const fetchDocuments = useCallback(async (showLoading: boolean) => {
    if (!projectId) return;
    const session = sessionRef.current;
    const request = ++requestRef.current;
    const mutation = mutationRef.current;
    const active = () => session === sessionRef.current && request === requestRef.current;
    if (showLoading) setIsLoading(true);
    try {
      const items = await documentsApi.list(projectId);
      if (active() && mutation === mutationRef.current) {
        setResult({ projectId, documents: items });
        setError(null);
      }
    } catch (err) {
      if (active()) setError({ projectId, message: friendlyErrorMessage(err, "دریافت فهرست اسناد ناموفق بود.") });
    } finally {
      if (active()) setIsLoading(false);
    }
  }, [projectId]);

  const refresh = useCallback(() => fetchDocuments(true), [fetchDocuments]);
  useEffect(() => {
    sessionRef.current += 1;
    const timer = setTimeout(() => {
      setRetryingIds([]);
      setDeletingId(null);
      retryingRef.current = new Set();
      void refresh();
    }, 0);
    return () => {
      sessionRef.current += 1;
      requestRef.current += 1;
      clearTimeout(timer);
    };
  }, [refresh]);

  const hasProcessing = documents.some((document) => document.status === "processing");
  useEffect(() => {
    if (!projectId || !hasProcessing) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      await fetchDocuments(false);
      if (!stopped) timer = setTimeout(poll, 3000);
    };
    timer = setTimeout(poll, 3000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [projectId, hasProcessing, fetchDocuments]);

  const mergeDocuments = useCallback((incoming: Document[]) => {
    if (!projectId) return;
    mutationRef.current += 1;
    setResult((current) => {
      const known = current?.projectId === projectId ? current.documents : [];
      return { projectId, documents: [...new Map([...known, ...incoming].map((document) => [document.id, document])).values()] };
    });
  }, [projectId]);

  const uploadBatch: BatchUploadHandler = useCallback(async (files, onBatch) => {
    if (!projectId) throw new Error("ابتدا پروژه را انتخاب کنید.");
    const session = sessionRef.current;
    const active = () => session === sessionRef.current;
    return uploadFileBatches(files, async (batch) => {
      const response = await documentsApi.uploadBatch(projectId, batch);
      if (active()) mergeDocuments(response.items.flatMap((item) => item.status === "accepted" ? [item.document] : []));
      return response;
    }, onBatch, active);
  }, [projectId, mergeDocuments]);

  const retry = useCallback(async (documentId: string) => {
    if (!projectId || retryingRef.current.has(documentId)) return;
    const session = sessionRef.current;
    const active = () => session === sessionRef.current;
    retryingRef.current.add(documentId);
    setRetryingIds([...retryingRef.current]);
    mutationRef.current += 1;
    try {
      const document = await documentsApi.retry(projectId, documentId);
      if (active()) { mergeDocuments([document]); setError(null); }
    } catch (err) {
      if (active()) setError({ projectId, message: friendlyErrorMessage(err, "تلاش مجدد ناموفق بود.") });
      throw err;
    } finally {
      if (active()) { retryingRef.current.delete(documentId); setRetryingIds([...retryingRef.current]); }
    }
  }, [projectId, mergeDocuments]);

  const retryMany = useCallback(async (ids: string[]) => {
    const session = sessionRef.current;
    const pending = [...new Set(ids)].filter((id) => documents.some((document) => document.id === id && document.status === "failed"));
    const failures: string[] = [];
    let next = 0;
    await Promise.all(Array.from({ length: Math.min(2, pending.length) }, async () => {
      while (next < pending.length && session === sessionRef.current) {
        const id = pending[next++];
        if (id) await retry(id).catch((error) => {
          const filename = documents.find((document) => document.id === id)?.filename ?? id;
          failures.push(`${filename}: ${friendlyErrorMessage(error, "تلاش مجدد ناموفق بود.")}`);
        });
      }
    }));
    if (failures.length && session === sessionRef.current && projectId) setError({ projectId, message: failures.join("؛ ") });
  }, [documents, retry, projectId]);

  const remove = useCallback(async (documentId: string) => {
    if (!projectId) return;
    const session = sessionRef.current;
    setDeletingId(documentId);
    mutationRef.current += 1;
    try {
      await documentsApi.remove(projectId, documentId);
      if (session === sessionRef.current) {
        mutationRef.current += 1;
        setResult((current) => current?.projectId === projectId ? { projectId, documents: current.documents.filter((document) => document.id !== documentId) } : current);
        setError(null);
      }
    } catch (err) {
      if (session === sessionRef.current) setError({ projectId, message: friendlyErrorMessage(err, "حذف سند ناموفق بود.") });
      throw err;
    } finally {
      if (session === sessionRef.current) setDeletingId(null);
    }
  }, [projectId]);

  return { documents, isLoading, error, deletingId, retryingIds, refresh, uploadBatch, retry, retryMany, remove };
}
