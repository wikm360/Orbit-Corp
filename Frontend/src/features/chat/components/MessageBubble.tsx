import { Markdown } from "@/shared/components/ui/Markdown";

import { AgentStep, ChatMessage, SqlResultArtifact } from "../types";
import { AgentActivityBanner } from "./AgentActivityBanner";
import { SourceCitationList } from "./SourceCitation";
import { SqlResultCard } from "./SqlResultCard";

export function MessageBubble({
  message,
  isPending = false,
  activeSteps,
  senderName,
  replyPreview,
}: {
  message: ChatMessage;
  isPending?: boolean;
  activeSteps?: AgentStep[];
  senderName?: string;
  replyPreview?: string;
}) {
  const isUser = message.sender_type === "user";

  if (isUser) {
    return (
      <div className="flex justify-start py-2">
        <div className="max-w-[88%] rounded-2xl rounded-br-md border border-slate-200/70 bg-[#eaf0f5] px-5 py-3 text-[15px] leading-7 text-gray-900 sm:max-w-[75%]">
          {senderName && <p className="text-xs font-semibold text-brand-700">{senderName}</p>}
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  // The server swaps accounting replies for a placeholder (and drops the artifacts) for readers without accounting access.
  const withheldFinancial = Boolean((message as unknown as { contains_financial?: boolean }).contains_financial) && (message.artifacts ?? []).length === 0;
  const stepsToRender = isPending ? activeSteps : message.steps;

  return (
    <div className="flex gap-3 py-3">
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[#142b40] text-teal-300 shadow-sm">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M12 2.75 14.1 9.9 21.25 12l-7.15 2.1L12 21.25 9.9 14.1 2.75 12 9.9 9.9 12 2.75Z" />
        </svg>
      </div>
      <div className="min-w-0 flex-1 rounded-2xl border border-slate-200/60 bg-white px-4 py-3 text-[15px] leading-8 text-gray-900">
          {replyPreview && <p className="mb-2 border-r-2 border-brand-200 pr-2 text-xs leading-5 text-gray-500">در پاسخ به: {replyPreview}</p>}
          {stepsToRender && stepsToRender.length > 0 && (
            <div className="mb-3">
              <AgentActivityBanner steps={stepsToRender} isCompleted={!isPending} />
            </div>
          )}
          {withheldFinancial ? (
            <p className="py-1 text-sm text-gray-500">🔒 این پاسخ شامل اطلاعات مالی است و برای مشاهده‌ی آن مجوز دسترسی مالی لازم است.</p>
          ) : message.content ? (
            <Markdown content={message.content} />
          ) : isPending ? (
            <span className="inline-flex gap-1 py-2" aria-label="در حال آماده‌سازی پاسخ">
              {[0, 1, 2].map((item) => (
                <span
                  key={item}
                  className="h-1.5 w-1.5 animate-pulse rounded-full bg-gray-500"
                  style={{ animationDelay: `${item * 150}ms` }}
                />
              ))}
            </span>
          ) : (
            <p className="py-1 text-sm text-gray-400">پاسخی دریافت نشد.</p>
          )}
          {(message.artifacts ?? [])
            .filter((artifact): artifact is SqlResultArtifact => artifact.type === "sql_result")
            .map((artifact) => <SqlResultCard key={artifact.query_id} artifact={artifact} />)}
          <SourceCitationList sources={message.sources} />
      </div>
    </div>
  );
}
