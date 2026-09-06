import { Markdown } from "@/shared/components/ui/Markdown";

import { ChatMessage } from "../types";
import { SourceCitationList } from "./SourceCitation";

export function MessageBubble({
  message,
  isPending = false,
}: {
  message: ChatMessage;
  isPending?: boolean;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-start py-2">
        <div className="max-w-[88%] rounded-3xl rounded-br-lg bg-[#f4f4f4] px-4 py-2.5 text-[15px] leading-7 text-gray-900 sm:max-w-[75%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 py-3">
      <div className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border border-gray-200 bg-white text-brand-700 shadow-sm">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M12 2.75 14.1 9.9 21.25 12l-7.15 2.1L12 21.25 9.9 14.1 2.75 12 9.9 9.9 12 2.75Z" />
        </svg>
      </div>
      <div className="min-w-0 flex-1 pt-0.5 text-[15px] leading-8 text-gray-900">
          {message.content ? (
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
          <SourceCitationList sources={message.sources} />
      </div>
    </div>
  );
}
