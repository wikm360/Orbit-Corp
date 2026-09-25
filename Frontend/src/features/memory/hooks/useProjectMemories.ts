"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { memoryApi } from "../api/memoryApi";
import type { ProjectMemory, ProjectMemoryCreate, ProjectMemoryUpdate } from "../types";

export function useProjectMemories(projectId: string | null) {
  const [memories, setMemories] = useState<ProjectMemory[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [mutationKey, setMutationKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);

  const refresh = useCallback(async () => {
    const sequence = ++requestSequence.current;
    if (!projectId) {
      setMemories([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await memoryApi.list(projectId);
      if (sequence === requestSequence.current) setMemories(data);
    } catch (err) {
      if (sequence === requestSequence.current) {
        setMemories([]);
        setError(friendlyErrorMessage(err, "دریافت حافظه پروژه ناموفق بود."));
      }
    } finally {
      if (sequence === requestSequence.current) setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const mutate = useCallback(async <T,>(key: string, action: () => Promise<T>): Promise<T> => {
    setMutationKey(key);
    setError(null);
    try {
      return await action();
    } catch (err) {
      setError(friendlyErrorMessage(err, "ذخیره تغییرات حافظه ناموفق بود."));
      throw err;
    } finally {
      setMutationKey(null);
    }
  }, []);

  const createMemory = useCallback(async (payload: ProjectMemoryCreate) => {
    if (!projectId) throw new Error("پروژه‌ای انتخاب نشده است.");
    return mutate("create", async () => {
      const created = await memoryApi.create(projectId, payload);
      setMemories((current) => [created, ...current]);
      return created;
    });
  }, [mutate, projectId]);

  const updateMemory = useCallback(async (memoryId: string, payload: ProjectMemoryUpdate) => {
    if (!projectId) throw new Error("پروژه‌ای انتخاب نشده است.");
    return mutate(`update:${memoryId}`, async () => {
      const updated = await memoryApi.update(projectId, memoryId, payload);
      setMemories((current) => current.map((item) => item.id === updated.id ? updated : item));
      return updated;
    });
  }, [mutate, projectId]);

  const removeMemory = useCallback(async (memoryId: string) => {
    if (!projectId) throw new Error("پروژه‌ای انتخاب نشده است.");
    return mutate(`delete:${memoryId}`, async () => {
      await memoryApi.remove(projectId, memoryId);
      setMemories((current) => current.filter((item) => item.id !== memoryId));
    });
  }, [mutate, projectId]);

  return {
    memories,
    isLoading,
    mutationKey,
    error,
    refresh,
    createMemory,
    updateMemory,
    removeMemory,
  };
}
