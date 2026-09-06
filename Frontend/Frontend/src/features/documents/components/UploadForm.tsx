"use client";

import { FormEvent, useEffect, useState } from "react";

import { ApiError } from "@/shared/lib/apiClient";
import { Button } from "@/shared/components/ui/Button";

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

  useEffect(() => {
    documentsApi.myTeams().then((options) => {
      setTeams(options);
      if (options[0]) setTeamId(options[0].id);
    });
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || !teamId) return;
    setError(null);
    setIsUploading(true);
    try {
      await onUpload(teamId, file);
      setFile(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  if (teams.length === 0) {
    return (
      <p className="text-sm text-gray-400">
        شما عضو هیچ تیمی نیستید. ابتدا از پنل ادمین به یک تیم اضافه شوید.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">تیم</label>
        <select
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">فایل</label>
        <input
          type="file"
          accept=".pdf,.docx,.pptx,.xlsx,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
      </div>

      <Button type="submit" isLoading={isUploading} disabled={!file}>
        آپلود
      </Button>

      {error && <p className="w-full text-sm text-red-600">{error}</p>}
    </form>
  );
}
