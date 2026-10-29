import { useState } from "react";
import { OrbitIcon } from "@/shared/components/ui/OrbitIcon";
import { agentStatusDetail, agentStatusLabel, agentToolIcon } from "../lib/agentStatus";
import { AgentStatus, AgentStep } from "../types";

export interface AgentActivityBannerProps {
  status?: AgentStatus | null;
  steps?: AgentStep[];
  isCompleted?: boolean;
  defaultExpanded?: boolean;
}

export function AgentActivityBanner({
  status,
  steps,
  isCompleted = false,
  defaultExpanded,
}: AgentActivityBannerProps) {
  // Synthesize steps from status if steps array is empty
  const allSteps: AgentStep[] =
    steps && steps.length > 0
      ? steps
      : status
      ? [
          {
            id: "initial",
            status: status.status,
            tool: status.tool,
            args: status.args,
            label: agentStatusLabel(status),
            detail: agentStatusDetail(status),
            state: isCompleted ? "completed" : "running",
            timestamp: 0,
          },
        ]
      : [];

  const [isExpanded, setIsExpanded] = useState(defaultExpanded ?? !isCompleted);

  if (allSteps.length === 0) return null;

  const runningStep = allSteps.find((s) => s.state === "running");
  const stepCount = allSteps.length;

  return (
    <div
      role="status"
      className="my-2 w-full max-w-full overflow-hidden rounded-2xl border border-teal-100/90 bg-teal-50/40 text-xs shadow-sm backdrop-blur-sm transition-all duration-200"
    >
      {/* Header / Accordion Toggle */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-right transition hover:bg-teal-50/80 focus:outline-none"
        aria-expanded={isExpanded}
        aria-label="نمایش یا پنهان‌سازی مراحل انجام کار توسط دستیار"
      >
        <div className="flex min-w-0 items-center gap-2.5">
          {isCompleted ? (
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-lg bg-emerald-100/80 text-emerald-700">
              <OrbitIcon name="check" className="h-3 w-3 stroke-[2.5]" />
            </span>
          ) : (
            <span className="relative flex h-5 w-5 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
              <span className="absolute h-2 w-2 rounded-full bg-teal-600 animate-ping opacity-60" />
              <OrbitIcon name="spark" className="h-3.5 w-3.5" />
            </span>
          )}

          <div className="flex flex-wrap items-center gap-1.5 text-xs text-teal-900 font-medium">
            <span>
              {isCompleted
                ? `تکمیل شده در ${stepCount} مرحله`
                : "روند اجرای ایجنت و ابزارها"}
            </span>
            <span className="rounded-md bg-teal-100/80 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">
              {stepCount} {stepCount === 1 ? "گام" : "مرحله"}
            </span>
            {!isExpanded && runningStep && (
              <span className="text-[11px] font-normal text-teal-700/90">
                — {runningStep.label}
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 text-teal-600">
          <span className="text-[11px] font-normal opacity-80">
            {isExpanded ? "بستن" : "مشاهده مراحل"}
          </span>
          <span
            className={`transition-transform duration-200 ${
              isExpanded ? "rotate-180" : ""
            }`}
          >
            <OrbitIcon name="chevron" className="h-3.5 w-3.5" />
          </span>
        </div>
      </button>

      {/* Expanded Hierarchical Steps / Timeline */}
      {isExpanded && (
        <div className="border-t border-teal-100/60 bg-white/70 px-4 py-3">
          <div className="relative mr-2 space-y-3.5 border-r-2 border-teal-200/70 py-1 pr-4">
            {allSteps.map((step, index) => {
              const isCurrent = step.state === "running";
              const isFailed = step.state === "failed";

              return (
                <div key={step.id || index} className="relative group text-right">
                  {/* Timeline Node on vertical line */}
                  <span
                    className={`absolute -right-[1.45rem] flex h-5 w-5 items-center justify-center rounded-full shadow-xs transition-colors ${
                      isCurrent
                        ? "border-2 border-teal-500 bg-white text-teal-600 ring-4 ring-teal-100 animate-pulse"
                        : isFailed
                        ? "border border-red-300 bg-red-50 text-red-600"
                        : "border border-emerald-300 bg-emerald-50 text-emerald-600"
                    }`}
                  >
                    {isCurrent ? (
                      <span className="h-2 w-2 rounded-full bg-teal-600" />
                    ) : isFailed ? (
                      <span className="text-[10px] font-bold">!</span>
                    ) : (
                      <OrbitIcon name="check" className="h-3 w-3 stroke-[2.5]" />
                    )}
                  </span>

                  {/* Step Content */}
                  <div className="min-w-0 pr-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 font-medium text-slate-800 text-[12px]">
                        <OrbitIcon
                          name={agentToolIcon(step.tool, step.status)}
                          className="h-3.5 w-3.5 shrink-0 text-teal-700"
                        />
                        <span>{step.label}</span>
                      </div>

                      {/* State Pill */}
                      {isCurrent ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2 py-0.5 text-[10px] font-medium text-teal-800">
                          <span className="h-1.5 w-1.5 rounded-full bg-teal-600 animate-ping" />
                          در حال انجام...
                        </span>
                      ) : isFailed ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">
                          خطا در این گام
                        </span>
                      ) : (
                        <span className="text-[10px] text-emerald-700 font-medium">
                          انجام شد
                        </span>
                      )}
                    </div>

                    {/* Step Detail / Args Preview */}
                    {step.detail && (
                      <div className="mt-1 rounded-lg border border-slate-100 bg-slate-50/80 px-2.5 py-1 text-[11px] text-slate-600 break-words">
                        <bdi>{step.detail}</bdi>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
