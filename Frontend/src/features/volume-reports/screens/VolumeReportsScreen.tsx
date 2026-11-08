"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { AttentionList } from "../components/AttentionList";
import { EmptyState, ErrorBox, LoadingBlock, Tabs } from "../components/common";
import { ProjectPicker } from "../components/ProjectPicker";
import { ReportsList } from "../components/ReportsList";
import { SettingsPanel } from "../components/SettingsPanel";
import { useVolumeEnabled } from "../hooks/useVolumeEnabled";
import { useWorkspaceProjects } from "../hooks/useWorkspaceProjects";

type TabId = "reports" | "review" | "settings";
const TABS: { id: TabId; label: string }[] = [{ id: "reports", label: "گزارش‌ها" }, { id: "review", label: "صف بازبینی" }, { id: "settings", label: "تنظیمات" }];

function Inner() {
  const router = useRouter();
  const params = useSearchParams();
  const enabled = useVolumeEnabled();
  const { projects, canEditSettings, loading, error, reload } = useWorkspaceProjects();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "reports") as TabId;
  const projectId = params.get("project") ?? projects[0]?.id ?? "";

  useEffect(() => { if (enabled === false) router.replace("/chat"); }, [enabled, router]);

  function navigate(next: { tab?: TabId; project?: string }) {
    const q = new URLSearchParams(params.toString());
    if (next.tab) q.set("tab", next.tab);
    if (next.project) q.set("project", next.project);
    router.replace(`/volume-reports?${q.toString()}`);
  }

  if (enabled === null || loading) return <LoadingBlock />;
  if (enabled === false) return null;
  if (error) return <div className="p-6"><ErrorBox error={error} onRetry={() => void reload()} /></div>;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">گزارش حجم عملیات</h1>
          <p className="text-xs text-slate-500">مجموع حجم فیزیکی آیتم‌های کلیدی (از جمله لوله‌گذاری) به تفکیک کارگاه، شرکت و هلدینگ</p>
        </div>
        <Link href={projectId ? `/volume-reports/new?project=${projectId}` : "/volume-reports/new"} className="inline-flex items-center rounded-xl bg-[#163b48] px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-teal-700">ساخت گزارش جدید</Link>
      </header>

      <Tabs<TabId> tabs={TABS.map((t) => ({ ...t }))} value={tab} onChange={(id) => navigate({ tab: id })} />

      {tab !== "settings" && (
        projects.length === 0 ? (
          <EmptyState title="پروژه‌ای در دسترس نیست" hint="برای دیدن یا ساخت گزارش باید عضو یک پروژه باشید." />
        ) : (
          <div className="space-y-4">
            <ProjectPicker projects={projects} value={projectId} onChange={(id) => navigate({ project: id })} />
            {tab === "reports" ? <ReportsList projectId={projectId} /> : <AttentionList projectId={projectId} />}
          </div>
        )
      )}
      {tab === "settings" && <SettingsPanel canEdit={canEditSettings} />}
    </div>
  );
}

export function VolumeReportsScreen() {
  return <Suspense fallback={<LoadingBlock />}><Inner /></Suspense>;
}
