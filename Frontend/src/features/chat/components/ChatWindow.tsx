import { KeyboardEvent, useEffect, useRef, useState } from "react";

import { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { MentionDropdown, MentionItem } from "./MentionDropdown";
import { AgentActivityBanner } from "./AgentActivityBanner";

export interface AvailableDoc {
  id: string;
  filename: string;
  isPersonal?: boolean;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  isLoadingConversation?: boolean;
  error: string | null;
  onSend: (text: string) => void;
  senderNames?: Record<string, string>;
  group?: boolean;
  onUpload?: (file: File) => Promise<void>;
  availableDocuments?: AvailableDoc[];
  agentStatusText?: string;
}

const MAX_TEXTAREA_HEIGHT_PX = 200;
const AI_TRIGGER_TOKEN = process.env.NEXT_PUBLIC_AI_TRIGGER_TOKEN ?? "@bot";

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
  senderNames = {},
  group = false,
  onUpload,
  availableDocuments = [],
  agentStatusText,
}: ChatWindowProps) {
  const [draft, setDraft] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Mention State
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStartIndex, setMentionStartIndex] = useState<number>(-1);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);

  function removeAttachedDoc(fileName: string) {
    setAttachedFiles((prev) => prev.filter((name) => name !== fileName));
  }

  // Generate mention suggestions
  const mentionItems: MentionItem[] = [];
  if (mentionQuery !== null) {
    const q = mentionQuery.toLowerCase();
    if ("bot".includes(q) || "بات".includes(q) || "دستیار".includes(q)) {
      mentionItems.push({
        id: "bot",
        label: AI_TRIGGER_TOKEN,
        type: "bot",
        subtitle: "صدا زدن دستیار هوشمند",
      });
    }
    availableDocuments.forEach((doc) => {
      if (doc.filename.toLowerCase().includes(q)) {
        mentionItems.push({
          id: doc.id,
          label: `@${doc.filename}`,
          type: doc.isPersonal ? "personal_doc" : "project_doc",
          subtitle: doc.isPersonal ? "سند شخصی شما" : "سند سازمانی پروژه",
        });
      }
    });
  }

  function handleDraftChange(text: string) {
    setDraft(text);
    const cursor = textareaRef.current?.selectionStart ?? text.length;
    const textBeforeCursor = text.slice(0, cursor);
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");

    if (lastAtIndex !== -1) {
      const charBeforeAt = lastAtIndex > 0 ? textBeforeCursor[lastAtIndex - 1] : " ";
      if (charBeforeAt === " " || charBeforeAt === "\n") {
        const query = textBeforeCursor.slice(lastAtIndex + 1);
        if (!query.includes(" ")) {
          setMentionQuery(query);
          setMentionStartIndex(lastAtIndex);
          setSelectedMentionIndex(0);
          return;
        }
      }
    }
    setMentionQuery(null);
    setMentionStartIndex(-1);
  }

  function applyMention(item: MentionItem) {
    if (mentionStartIndex === -1 || !textareaRef.current) return;
    const cursor = textareaRef.current.selectionStart;
    const before = draft.slice(0, mentionStartIndex);
    const after = draft.slice(cursor);
    const insertion = `${item.label} `;
    const newText = `${before}${insertion}${after}`;
    setDraft(newText);
    setMentionQuery(null);
    setMentionStartIndex(-1);

    // If a document was mentioned, auto add to attached badge list if not present
    if (item.type !== "bot") {
      const cleanName = item.label.replace(/^@/, "");
      setAttachedFiles((prev) => (prev.includes(cleanName) ? prev : [...prev, cleanName]));
    }

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newCursorPos = before.length + insertion.length;
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }
    }, 0);
  }

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
  }, [messages, isStreaming, agentStatusText]);

  function submit() {
    if (!draft.trim() || isStreaming) return;
    onSend(draft.trim());
    setDraft("");
    setMentionQuery(null);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (mentionQuery !== null && mentionItems.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedMentionIndex((prev) => (prev + 1) % mentionItems.length);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedMentionIndex((prev) => (prev - 1 + mentionItems.length) % mentionItems.length);
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        const item = mentionItems[selectedMentionIndex];
        if (item) applyMention(item);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setMentionQuery(null);
        return;
      }
    }

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
                {group ? `با اعضای پروژه گفتگو کنید. برای درخواست پاسخ از دستیار، پیام را با ${AI_TRIGGER_TOKEN} شروع کنید.` : "درباره اسناد، قراردادها و دانش سازمان سؤال کنید؛ پاسخ‌ها با استناد به منابع در دسترس شما ارائه می‌شوند."}
              </p>
              {!group && <div className="mt-8 grid gap-2 text-right sm:grid-cols-2">
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
              </div>}
            </div>
          ) : (
            messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isPending={message.id.startsWith("pending-") || (isStreaming && index === messages.length - 1)}
                senderName={group && message.sender_id ? senderNames[message.sender_id] ?? message.sender_id.slice(0, 8) : undefined}
                replyPreview={group && message.reply_to_message_id ? messages.find((item) => item.id === message.reply_to_message_id)?.content.slice(0, 90) : undefined}
              />
            ))
          )}
          {isStreaming && (
            <div className="flex items-center justify-start py-1">
              <AgentActivityBanner isStreaming={isStreaming} statusText={agentStatusText} />
            </div>
          )}
          {(error || uploadError) && (
            <div role="alert" className="mx-auto w-full max-w-2xl rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-center text-sm text-red-700">
              {error ?? uploadError}
            </div>
          )}
          {uploadSuccess && (
            <div role="status" className="mx-auto w-full max-w-2xl rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-2.5 text-center text-xs text-emerald-800">
              {uploadSuccess}
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="relative shrink-0 bg-gradient-to-t from-white via-white to-white/0 px-3 pb-3 pt-2 sm:px-6"
      >
        {mentionQuery !== null && mentionItems.length > 0 && (
          <MentionDropdown
            items={mentionItems}
            selectedIndex={selectedMentionIndex}
            onSelect={applyMention}
            onClose={() => setMentionQuery(null)}
          />
        )}

        {attachedFiles.length > 0 && (
          <div className="mx-auto mb-2 flex max-w-3xl flex-wrap items-center gap-2 px-1">
            <span className="text-xs text-gray-500">اسناد پیوست‌شده به گفتگو:</span>
            {attachedFiles.map((name) => (
              <span
                key={name}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-700"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5 text-brand-600">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6M8 13h8M8 17h6" />
                </svg>
                <span className="max-w-[180px] truncate">{name}</span>
                <button
                  type="button"
                  onClick={() => removeAttachedDoc(name)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label={`حذف ${name}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="mx-auto flex w-full max-w-3xl items-end gap-1 rounded-[26px] border border-transparent bg-[#f4f4f4] p-2 shadow-[0_2px_12px_rgba(0,0,0,0.06)] transition focus-within:border-gray-300">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-gray-600 transition hover:bg-black/[0.06] disabled:opacity-60"
            aria-label="افزودن سند به این گفتگو"
            title="افزودن سند به این گفتگو"
          >
            {uploading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-gray-800" />
            ) : (
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                <path strokeLinecap="round" d="M12 5v14M5 12h14" />
              </svg>
            )}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.pptx,.xlsx,.txt"
            className="hidden"
            aria-label="فایل پیوست گفتگو"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setUploadError(null);
              setUploadSuccess(null);
              const ALLOWED = [".pdf", ".docx", ".pptx", ".xlsx", ".txt"];
              const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
              if (!ALLOWED.includes(ext)) {
                setUploadError("فرمت فایل مجاز نیست (فقط PDF، DOCX، PPTX، XLSX یا TXT).");
                event.target.value = "";
                return;
              }
              if (file.size > 50 * 1024 * 1024) {
                setUploadError("حجم فایل نباید بیشتر از ۵۰ مگابایت باشد.");
                event.target.value = "";
                return;
              }
              setUploading(true);
              try {
                if (onUpload) {
                  await onUpload(file);
                }
                setAttachedFiles((prev) => (prev.includes(file.name) ? prev : [...prev, file.name]));
                setUploadSuccess(`سند «${file.name}» به این گفتگو پیوست شد و پاسخ‌ها با استناد به آن خواهند بود.`);
                setTimeout(() => setUploadSuccess(null), 5000);
              } catch (err) {
                setUploadError(err instanceof Error ? err.message : "آپلود ناموفق بود.");
              } finally {
                setUploading(false);
                event.target.value = "";
              }
            }}
          />
          <textarea
            ref={textareaRef}
            rows={1}
            aria-label="پیام"
            className="min-w-0 flex-1 resize-none overflow-y-auto bg-transparent px-2 py-1.5 text-[15px] leading-7 text-gray-900 outline-none placeholder:text-gray-500 disabled:cursor-not-allowed disabled:opacity-60"
            style={{ maxHeight: MAX_TEXTAREA_HEIGHT_PX }}
            placeholder={
              group
                ? `پیام پروژه؛ برای دستیار با ${AI_TRIGGER_TOKEN} شروع کنید یا با @ سندی منشن کنید...`
                : attachedFiles.length > 0
                ? "درباره سند پیوست‌شده بپرسید..."
                : "پیام خود را بنویسید؛ با تایپ @ می‌توانید دستیار یا سندی را منشن کنید..."
            }
            value={draft}
            onChange={(e) => handleDraftChange(e.target.value)}
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
