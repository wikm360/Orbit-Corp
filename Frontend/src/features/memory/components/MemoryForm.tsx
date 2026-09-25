"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import type { MemoryCategory, ProjectMemoryCreate } from "../types";

const CATEGORY_OPTIONS: Array<{ value: MemoryCategory; label: string }> = [
  { value: "technical_decision", label: "تصمیم فنی" },
  { value: "timeline", label: "زمان‌بندی" },
  { value: "business_rule", label: "قانون کسب‌وکار" },
  { value: "convention", label: "قرارداد / عرف تیمی" },
];

interface MemoryFormProps {
  initialValue?: ProjectMemoryCreate;
  submitLabel: string;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (payload: ProjectMemoryCreate) => Promise<void>;
}

export function MemoryForm({ initialValue, submitLabel, isSubmitting, onCancel, onSubmit }: MemoryFormProps) {
  const [factText, setFactText] = useState(initialValue?.fact_text ?? "");
  const [category, setCategory] = useState<MemoryCategory>(initialValue?.category ?? "technical_decision");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedText = factText.trim();
    if (!normalizedText) {
      setError("متن حافظه را وارد کنید.");
      return;
    }

    setError(null);
    try {
      await onSubmit({ fact_text: normalizedText, category });
    } catch (err) {
      setError(friendlyErrorMessage(err, "ذخیره این مورد ناموفق بود."));
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="memory-fact-text" className="mb-2 block text-sm font-medium text-gray-700">
          واقعیت یا تصمیم پروژه
        </label>
        <textarea
          id="memory-fact-text"
          value={factText}
          onChange={(event) => setFactText(event.target.value)}
          rows={5}
          autoFocus
          maxLength={4000}
          placeholder="مثلاً: انتشار نسخه‌های اصلی فقط پنج‌شنبه‌ها انجام می‌شود."
          className="w-full resize-y rounded-xl border border-gray-200 bg-white px-3.5 py-3 text-sm leading-7 text-gray-900 shadow-sm transition placeholder:text-gray-400 focus:border-teal-400 focus:outline-none focus:ring-4 focus:ring-teal-100"
        />
        <div className="mt-1.5 flex items-center justify-between text-[11px] text-gray-400">
          <span>شفاف و مستقل بنویسید تا در گفتگوهای بعدی قابل استفاده باشد.</span>
          <span className="ltr">{factText.length.toLocaleString("fa-IR")} / ۴۰۰۰</span>
        </div>
      </div>

      <div>
        <label htmlFor="memory-category" className="mb-2 block text-sm font-medium text-gray-700">دسته‌بندی</label>
        <Select
          id="memory-category"
          value={category}
          onValueChange={(nextValue) => setCategory(nextValue as MemoryCategory)}
          options={CATEGORY_OPTIONS}
        />
      </div>

      {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2.5 text-sm text-red-700">{error}</p>}

      <div className="flex flex-row-reverse gap-2 border-t border-gray-100 pt-4">
        <Button type="submit" isLoading={isSubmitting} disabled={!factText.trim()}>{submitLabel}</Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>انصراف</Button>
      </div>
    </form>
  );
}

export { CATEGORY_OPTIONS };
