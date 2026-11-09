"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/shared/components/ui/Button";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import type { CompanyNarrative } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock } from "./common";

interface CompanyEntry {
  id: string;
  name: string;
}

export function NarrativesPanel({
  reportId,
  refreshKey = 0,
}: {
  reportId: string;
  refreshKey?: number;
}) {
  const [companies, setCompanies] = useState<CompanyEntry[]>([]);
  const [narratives, setNarratives] = useState<Record<string, CompanyNarrative>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [compRes, narrRes] = await Promise.all([
        volumeReportApi.results(reportId, "company"),
        volumeReportApi.narratives(reportId),
      ]);
      const uniqueComps = new Map<string, string>();
      for (const row of compRes.rows) {
        if (row.company_id && row.company) {
          uniqueComps.set(row.company_id, row.company);
        }
      }
      const compList = Array.from(uniqueComps.entries()).map(([id, name]) => ({ id, name }));
      setCompanies(compList);
      setNarratives(narrRes || {});
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    runSoon(() => void load());
  }, [load, refreshKey]);

  const handleRawChange = (companyId: string, companyName: string, text: string) => {
    setNarratives((prev) => ({
      ...prev,
      [companyId]: {
        company_name: companyName,
        raw_text: text,
        items: prev[companyId]?.items ?? [],
        updated_at: prev[companyId]?.updated_at,
      },
    }));
    setSaveSuccess(false);
  };

  const handleItemsChange = (companyId: string, companyName: string, textBlock: string) => {
    const rawBlocks = textBlock.split("\n\n").map((b) => b.trim()).filter(Boolean);
    setNarratives((prev) => ({
      ...prev,
      [companyId]: {
        company_name: companyName,
        raw_text: prev[companyId]?.raw_text ?? "",
        items: rawBlocks,
        updated_at: new Date().toISOString(),
      },
    }));
    setSaveSuccess(false);
  };

  const handleGenerate = async (companyId: string, companyName: string) => {
    const current = narratives[companyId];
    if (!current?.raw_text?.trim()) return;

    setGeneratingId(companyId);
    setError(null);
    try {
      const res = await volumeReportApi.generateNarrative(reportId, {
        company_id: companyId,
        company_name: companyName,
        raw_text: current.raw_text,
      });

      const updated = {
        company_name: companyName,
        raw_text: current.raw_text,
        items: res.items,
        updated_at: new Date().toISOString(),
      };

      const nextNarratives = {
        ...narratives,
        [companyId]: updated,
      };

      setNarratives(nextNarratives);
      await volumeReportApi.saveNarratives(reportId, nextNarratives);
      setSaveSuccess(true);
    } catch (err) {
      setError(err);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleSaveAll = async () => {
    setSaving(true);
    setError(null);
    try {
      await volumeReportApi.saveNarratives(reportId, narratives);
      setSaveSuccess(true);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBox error={error} fallback="خطا در دریافت اطلاعات عملکرد شرکت‌ها" />;
  if (!companies.length) {
    return <EmptyState title="هیچ شرکتی در این گزارش ثبت نشده است." />;
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-white p-5 shadow-xs border border-slate-200/80">
        <div>
          <h2 className="text-base font-bold text-slate-900">گزارش عملکرد پروژه‌های عمرانی شرکت‌ها</h2>
          <p className="mt-1 text-xs text-slate-500">
            یادداشت‌های ارسالی مدیران پروژه را وارد کرده و با هوش مصنوعی به بندهای مدیریتی و ساختاریافته برای پرزنتیشن تبدیل کنید.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <span className="text-xs font-bold text-emerald-600">✓ تغییرات با موفقیت ذخیره شد</span>
          )}
          <Button size="sm" isLoading={saving} onClick={() => void handleSaveAll()}>
            ذخیره تغییرات
          </Button>
        </div>
      </div>

      {/* Companies List */}
      <div className="space-y-5">
        {companies.map((company) => {
          const narr = narratives[company.id] ?? {
            company_name: company.name,
            raw_text: "",
            items: [],
          };
          const isGenerating = generatingId === company.id;
          const itemsText = narr.items.join("\n\n");

          return (
            <Card
              key={company.id}
              title={
                <span className="flex items-center gap-2 text-sm font-bold text-[#252850]">
                  <span className="h-3 w-3 rounded-full bg-[#252850]" />
                  <span>{company.name}</span>
                </span>
              }
              actions={
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!narr.raw_text.trim() || isGenerating}
                  isLoading={isGenerating}
                  onClick={() => void handleGenerate(company.id, company.name)}
                >
                  ✨ تبدیل به گزارش با هوش مصنوعی
                </Button>
              }
            >
              <div className="grid gap-5 lg:grid-cols-2">
                {/* Raw Input Text */}
                <div className="flex flex-col">
                  <label
                    htmlFor={`raw-${company.id}`}
                    className="mb-1.5 flex items-center justify-between text-xs font-bold text-slate-700"
                  >
                    <span>یادداشت‌ها و متن خام دریافتی از مدیران پروژه:</span>
                    <span className="text-[11px] font-normal text-slate-400">متن پیام یا گزارش را اینجا پیست کنید</span>
                  </label>
                  <textarea
                    id={`raw-${company.id}`}
                    rows={7}
                    value={narr.raw_text}
                    onChange={(e) => handleRawChange(company.id, company.name, e.target.value)}
                    placeholder="مثال: پروژه زاهدان خاش ۱۵۰۰ متر طول لایه اساس تموم شد و مناقصات گردنه خرمافروشان و زرند بافق و دیهوک اسنادش اخذ شد..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs leading-relaxed text-slate-800 placeholder:text-slate-400 focus:border-[#252850] focus:bg-white focus:outline-none"
                    dir="auto"
                  />
                </div>

                {/* Structured / AI-Generated Items */}
                <div className="flex flex-col">
                  <label
                    htmlFor={`items-${company.id}`}
                    className="mb-1.5 flex items-center justify-between text-xs font-bold text-slate-700"
                  >
                    <span>بندهای ساختاریافته مدیریتی (نمایش در پرزنتیشن):</span>
                    <span className="text-[11px] font-normal text-slate-400">بین هر بند یک خط خالی بگذارید</span>
                  </label>
                  <textarea
                    id={`items-${company.id}`}
                    rows={7}
                    value={itemsText}
                    onChange={(e) => handleItemsChange(company.id, company.name, e.target.value)}
                    placeholder="پس از کلیک روی «تبدیل به گزارش با هوش مصنوعی»، بندهای ویرایش‌شده اینجا قرار می‌گیرند یا می‌توانید مستقیماً ویرایش کنید..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs leading-relaxed text-slate-800 placeholder:text-slate-400 focus:border-[#252850] focus:bg-white focus:outline-none"
                    dir="auto"
                  />
                  {narr.items.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-slate-500">
                      <span>تعداد بندهای ثبت‌شده:</span>
                      <span className="font-bold text-[#252850]">{narr.items.length} بند</span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
