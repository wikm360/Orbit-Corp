import Link from "next/link";
import { KeyboardEvent, useEffect, useRef, useState } from "react";

import { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  isLoadingConversation?: boolean;
  error: string | null;
  onSend: (text: string) => void;
}

const MAX_TEXTAREA_HEIGHT_PX = 200;

const SUGGESTIONS = [
  { title: "خلاصه قرارداد", text: "مهم‌ترین بندهای قرارداد را خلاصه کن" },
  { title: "تعهدات پیمانکار", text: "تعهدات پیمانکار را فهرست کن" },
  { title: "الزامات ایمنی", text: "الزامات ایمنی پروژه کدام‌اند؟" },
  { title: "یافتن پاسخ دقیق", text: "بر اساس اسناد، پاسخ دقیق همراه منبع بده" },
];

export function ChatWindow({
  messages,
  isStreaming,
  isLoadingConversation = false,
  error,
  onSend,
}: ChatWindowProps) {
  const [draft, setDraft] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [draft]);

  useEffect(() => {
    const area = scrollAreaRef.current;
    if (!area) return;
    area.scrollTo({ top: area.scrollHeight, behavior: messages.length > 2 ? "smooth" : "auto" });
  }, [messages, isStreaming]);

  function submit() {
    if (!draft.trim() || isStreaming) return;
    onSend(draft.trim());
    setDraft("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div
        ref={scrollAreaRef}
        role="log"
        aria-live="polite"
        aria-busy={isStreaming || isLoadingConversation}
        className="flex-1 overflow-y-auto overscroll-contain px-4 pt-2 sm:px-6"
      >
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col space-y-3 pb-6">
          {isLoadingConversation ? (
            <div className="m-auto flex items-center gap-3 text-sm text-gray-500">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-gray-800" />
              در حال بارگذاری گفتگو...
            </div>
          ) : messages.length === 0 ? (
            <div className="m-auto w-full max-w-2xl px-2 py-10 text-center">
              <div className="mx-auto grid h-11 w-11 place-items-center rounded-full border border-gray-200 bg-white shadow-sm">
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-6 w-6 text-brand-700">
                  <path d="M12 2.75 14.1 9.9 21.25 12l-7.15 2.1L12 21.25 9.9 14.1 2.75 12 9.9 9.9 12 2.75Z" fill="currentColor" />
                </svg>
              </div>
              <h1 className="mt-5 text-2xl font-semibold tracking-tight text-gray-900 sm:text-[28px]">
                چطور می‌توانم کمکتان کنم؟
              </h1>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-7 text-gray-500">
                درباره اسناد، قراردادها و دانش سازمان سؤال کنید؛ پاسخ‌ها با استناد به منابع در دسترس شما ارائه می‌شوند.
              </p>
              <div className="mt-8 grid gap-2 text-right sm:grid-cols-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion.title}
                    type="button"
                    onClick={() => onSend(suggestion.text)}
                    className="group rounded-2xl border border-gray-200 bg-white px-4 py-3 text-right transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-300"
                  >
                    <span className="block text-sm font-medium text-gray-800">{suggestion.title}</span>
                    <span className="mt-0.5 block truncate text-xs text-gray-400 transition group-hover:text-gray-500">{suggestion.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isPending={isStreaming && index === messages.length - 1}
              />
            ))
          )}
          {error && (
            <div role="alert" className="mx-auto w-full max-w-2xl rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-center text-sm text-red-700">
              {error}
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="shrink-0 bg-gradient-to-t from-white via-white to-white/0 px-3 pb-3 pt-2 sm:px-6"
      >
        <div className="mx-auto flex w-full max-w-3xl items-end gap-1 rounded-[26px] border border-transparent bg-[#f4f4f4] p-2 shadow-[0_2px_12px_rgba(0,0,0,0.06)] transition focus-within:border-gray-300">
          <Link
            href="/documents"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-gray-600 transition hover:bg-black/[0.06]"
            aria-label="افزودن سند"
            title="افزودن سند"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" d="M12 5v14M5 12h14" />
            </svg>
          </Link>
          <textarea
            ref={textareaRef}
            rows={1}
            aria-label="پیام"
            className="min-w-0 flex-1 resize-none overflow-y-auto bg-transparent px-2 py-1.5 text-[15px] leading-7 text-gray-900 outline-none placeholder:text-gray-500 disabled:cursor-not-allowed disabled:opacity-60"
            style={{ maxHeight: MAX_TEXTAREA_HEIGHT_PX }}
            placeholder="از اسناد سازمان بپرسید"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming || isLoadingConversation}
          />
          <button
            type="submit"
            disabled={!draft.trim() || isLoadingConversation || isStreaming}
            aria-label="ارسال پیام"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gray-900 text-white transition hover:bg-black disabled:bg-gray-300"
          >
            {isStreaming ? (
              <span className="h-3 w-3 rounded-sm bg-white" />
            ) : (
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="m7 11 5-5 5 5M12 18V6" />
              </svg>
            )}
          </button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] leading-5 text-gray-400">
          دستیار ممکن است اشتباه کند؛ اطلاعات مهم را با منبع اصلی تطبیق دهید.
        </p>
      </form>
    </div>
  );
}
