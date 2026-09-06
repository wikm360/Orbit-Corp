"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { documentsApi } from "../api/documentsApi";
import { TeamOption } from "../types";

interface UploadFormProps {
  onUpload: (teamId: string, file: File) => Promise<void>;
}

export function UploadForm({ onUpload }: UploadFormProps) {
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [teamId, setTeamId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingTeams, setIsLoadingTeams] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    documentsApi
      .myTeams()
      .then((options) => {
        if (cancelled) return;
        setTeams(options);
        if (options[0]) setTeamId(options[0].id);
      })
      .catch((err) => {
        if (!cancelled) setError(friendlyErrorMessage(err, "دریافت تیم‌ها ناموفق بود."));
      })
      .finally(() => {
        if (!cancelled) setIsLoadingTeams(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || !teamId) return;
    setError(null);
    setIsUploading(true);
    try {
      await onUpload(teamId, file);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(friendlyErrorMessage(err, "آپلود سند ناموفق بود."));
    } finally {
      setIsUploading(false);
    }
  }

  if (isLoadingTeams) {
    return <p className="text-sm text-gray-400">در حال دریافت تیم‌های شما...</p>;
  }

  if (teams.length === 0 && !error) {
    return (
      <p className="text-sm text-gray-400">
        شما عضو هیچ تیمی نیستید. ابتدا از پنل ادمین به یک تیم اضافه شوید.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="grid items-end gap-4 sm:grid-cols-[minmax(140px,0.6fr)_minmax(220px,1.4fr)_auto]">
      <div className="flex min-w-0 flex-col gap-1.5">
        <label htmlFor="document-team" className="text-sm font-medium text-gray-700">تیم مقصد</label>
        <select
          id="document-team"
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          className="h-11 rounded-xl border border-gray-200 bg-white px-3 text-sm outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
        >
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex min-w-0 flex-col gap-1.5">
        <label htmlFor="document-file" className="text-sm font-medium text-gray-700">فایل سند</label>
        <input
          ref={fileInputRef}
          id="document-file"
          type="file"
          accept=".pdf,.docx,.pptx,.xlsx,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="h-11 min-w-0 rounded-xl border border-gray-200 bg-white text-sm text-gray-500 file:ms-0 file:me-3 file:h-full file:border-0 file:border-l file:border-gray-200 file:bg-gray-50 file:px-4 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-50"
        />
      </div>

      <Button type="submit" isLoading={isUploading} disabled={!file || !teamId} className="h-11">
        آپلود
      </Button>

      {error && <p role="alert" className="text-sm text-red-600 sm:col-span-3">{error}</p>}
    </form>
  );
}
