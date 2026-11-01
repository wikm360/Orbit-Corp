"use client";

import type { Project } from "@/shared/types";

import { fieldClass } from "./common";

export function ProjectPicker({ projects, value, onChange, label = "پروژه" }: { projects: Project[]; value: string; onChange: (id: string) => void; label?: string }) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-700">
      <span className="shrink-0">{label}</span>
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} className={`${fieldClass} min-w-[12rem]`}>
        {projects.length === 0 && <option value="">پروژه‌ای در دسترس نیست</option>}
        {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
    </label>
  );
}
