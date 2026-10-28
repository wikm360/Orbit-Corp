import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/apiClient";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { documentsApi } from "../api/documentsApi";
import { uploadFileBatches } from "../lib/batchUpload";
import { type Clipboard, hasActiveWork, selectionFromKeys } from "../lib/fileManager";
import type { BatchUploadResponse, DocumentSearchHit, FileSelection, FolderListing, OnConflict } from "../types";
import type { BatchUploadHandler } from "./useBatchUpload";

const POLL_MS = 3000;

/** A move/copy refused with 409; the user may retry it keeping both names. */
export interface PendingConflict {
  message: string;
  retryWithRename: () => Promise<void>;
}

export function useFileManager(projectId: string | null) {
  const [folderId, setFolderId] = useState<string | null>(null);
  const [listing, setListing] = useState<FolderListing | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [clipboard, setClipboard] = useState<Clipboard | null>(null);
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState<PendingConflict | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<DocumentSearchHit[] | null>(null);
  const requestRef = useRef(0);
  const sessionRef = useRef(0);
  const folderRef = useRef<string | null>(null);

  // A different project is a different tree: drop everything that belonged to the old one.
  useEffect(() => {
    sessionRef.current += 1;
    const timer = setTimeout(() => {
      folderRef.current = null;
      setFolderId(null);
      setListing(null);
      setSelected(new Set());
      setClipboard((current) => (current && current.projectId === projectId ? current : null));
      setQuery("");
      setHits(null);
      setError(null);
    }, 0);
    return () => clearTimeout(timer);
  }, [projectId]);

  const load = useCallback(async (target: string | null, showLoading: boolean) => {
    if (!projectId) return;
    const session = sessionRef.current;
    const request = ++requestRef.current;
    if (showLoading) setIsLoading(true);
    try {
      const result = await documentsApi.listFiles(projectId, target);
      if (session !== sessionRef.current || request !== requestRef.current) return;
      setListing(result);
      setError(null);
      // Selection can only refer to what is still listed (polling may have removed items).
      setSelected((current) => {
        const alive = new Set([...result.documents.map((d) => `d:${d.id}`), ...result.folders.map((f) => `f:${f.folder.id}`)]);
        const next = new Set([...current].filter((key) => alive.has(key)));
        return next.size === current.size ? current : next;
      });
    } catch (err) {
      if (session !== sessionRef.current || request !== requestRef.current) return;
      // The folder was deleted elsewhere: fall back to the project root instead of showing an error forever.
      if (err instanceof ApiError && err.status === 404 && target !== null) {
        folderRef.current = null;
        setFolderId(null);
        return;
      }
      setError(friendlyErrorMessage(err, "دریافت فهرست اسناد ناموفق بود."));
    } finally {
      if (session === sessionRef.current && request === requestRef.current) setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    const timer = setTimeout(() => void load(folderId, true), 0);
    return () => clearTimeout(timer);
  }, [load, folderId]);

  const active = hasActiveWork(listing);
  useEffect(() => {
    if (!projectId || !active) return;
    const timer = setInterval(() => void load(folderRef.current, false), POLL_MS);
    return () => clearInterval(timer);
  }, [projectId, active, load]);

  const refresh = useCallback(() => load(folderRef.current, true), [load]);

  const open = useCallback((target: string | null) => {
    folderRef.current = target;
    setFolderId(target);
    setSelected(new Set());
    setQuery("");
    setHits(null);
  }, []);

  const toggle = useCallback((key: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  }, []);

  const selectAll = useCallback((all: boolean) => {
    setSelected(all && listing ? new Set([...listing.folders.map((f) => `f:${f.folder.id}`), ...listing.documents.map((d) => `d:${d.id}`)]) : new Set());
  }, [listing]);

  // Search is debounced and ignores answers that arrive after the query changed.
  useEffect(() => {
    if (!projectId || !query.trim()) {
      const timer = setTimeout(() => setHits(null), 0);
      return () => clearTimeout(timer);
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      documentsApi.searchFiles(projectId, query.trim())
        .then((result) => { if (!cancelled) setHits(result); })
        .catch((err) => { if (!cancelled) setError(friendlyErrorMessage(err, "جست‌وجو ناموفق بود.")); });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [projectId, query]);

  /** Runs one mutation: busy flag, error banner, then a fresh listing. Returns whether it succeeded. */
  const mutate = useCallback(async (action: () => Promise<unknown>, fallback: string): Promise<boolean> => {
    if (!projectId) return false;
    setBusy(true);
    try {
      await action();
      setError(null);
      return true;
    } catch (err) {
      setError(friendlyErrorMessage(err, fallback));
      return false;
    } finally {
      setBusy(false);
      void load(folderRef.current, false);
    }
  }, [projectId, load]);

  const createFolder = useCallback(async (name: string) => {
    if (!projectId) return;
    await documentsApi.createFolder(projectId, name, folderRef.current);
    void load(folderRef.current, false);
  }, [projectId, load]);

  const renameItem = useCallback(async (key: string, name: string) => {
    if (!projectId) return;
    if (key.startsWith("f:")) await documentsApi.renameFolder(projectId, key.slice(2), name);
    else await documentsApi.renameDocument(projectId, key.slice(2), name);
    void load(folderRef.current, false);
  }, [projectId, load]);

  const remove = useCallback((selection: FileSelection) =>
    mutate(() => documentsApi.deleteItems(projectId as string, selection), "حذف ناموفق بود."), [projectId, mutate]);

  const retry = useCallback((selection: FileSelection) =>
    mutate(async () => {
      const result = await documentsApi.retryItems(projectId as string, selection);
      if (result.count === 0) throw new Error("موردی برای تلاش مجدد پیدا نشد (فقط اسناد ناموفق، لغوشده یا فرمت‌های تازه‌پشتیبانی‌شده).");
    }, "تلاش مجدد ناموفق بود."), [projectId, mutate]);

  const cancel = useCallback((selection: FileSelection) =>
    mutate(async () => {
      const result = await documentsApi.cancelItems(projectId as string, selection);
      if (result.count === 0) throw new Error("هیچ‌کدام در حال پردازش نبودند.");
    }, "لغو ناموفق بود."), [projectId, mutate]);

  /** Move/copy `selection` into `target`; a name clash opens the conflict dialog instead of failing silently. */
  const place = useCallback(async (mode: "cut" | "copy", selection: FileSelection, target: string | null): Promise<boolean> => {
    if (!projectId) return false;
    const call = (onConflict: OnConflict) => (mode === "cut"
      ? documentsApi.move(projectId, selection, target, onConflict)
      : documentsApi.copy(projectId, selection, target, onConflict));
    setBusy(true);
    try {
      await call("fail");
      setError(null);
      if (mode === "cut") setClipboard(null);
      setSelected(new Set());
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict({
          message: err.message,
          retryWithRename: async () => {
            setConflict(null);
            await mutate(async () => { await call("rename"); if (mode === "cut") setClipboard(null); setSelected(new Set()); }, "عملیات ناموفق بود.");
          },
        });
      } else setError(friendlyErrorMessage(err, "عملیات ناموفق بود."));
      return false;
    } finally {
      setBusy(false);
      void load(folderRef.current, false);
    }
  }, [projectId, load, mutate]);

  const copyToClipboard = useCallback((mode: "cut" | "copy") => {
    if (!projectId) return;
    setClipboard({ mode, projectId, selection: selectionFromKeys(selected) });
  }, [projectId, selected]);

  const paste = useCallback(async () => {
    if (!clipboard || clipboard.projectId !== projectId) return;
    await place(clipboard.mode, clipboard.selection, folderRef.current);
  }, [clipboard, projectId, place]);

  const uploadFiles: BatchUploadHandler = useCallback(async (files, onBatch, onProgress) => {
    if (!projectId) throw new Error("ابتدا پروژه را انتخاب کنید.");
    const session = sessionRef.current;
    const target = folderRef.current;
    const live = () => session === sessionRef.current;
    return uploadFileBatches(files, async (batch, onFraction) => {
      const response: BatchUploadResponse = await documentsApi.uploadBatch(projectId, batch, target, onFraction);
      if (live()) void load(folderRef.current, false);
      return response;
    }, onBatch, live, onProgress);
  }, [projectId, load]);

  return {
    folderId, listing, isLoading, error, selected, clipboard, busy, conflict, query, hits,
    setQuery, setError, dismissConflict: () => setConflict(null),
    refresh, open, toggle, selectAll, createFolder, renameItem, remove, retry, cancel,
    place, copyToClipboard, paste, uploadFiles,
    dismissArchive: async (archiveId: string) => { if (projectId) await mutate(() => documentsApi.dismissArchive(projectId, archiveId), "حذف رکورد ناموفق بود."); },
  };
}
