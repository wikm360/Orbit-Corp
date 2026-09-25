import { KeyboardEvent, useEffect, useRef, useState } from "react";

import { OrbitIcon, OrbitIconName } from "@/shared/components/ui/OrbitIcon";
import { Document } from "@/features/documents/types";
import { AgentActivity, ChatMessage } from "../types";
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
  onUpload?: (file: File) => Promise<Document>;
  availableDocuments?: AvailableDoc[];
  agentActivities?: AgentActivity[];
  isSending?: boolean;
  isUploadingDocument?: boolean;
  isDocumentProcessing?: boolean;
  conversationDocuments?: Document[];
  onStop?: () => void;
  userName?: string;
}

const MAX_TEXTAREA_HEIGHT_PX = 200;
const AI_TRIGGER_TOKEN = process.env.NEXT_PUBLIC_AI_TRIGGER_TOKEN ?? "@bot";

const SUGGESTIONS: { title: string; text: string; description: string; icon: OrbitIconName; color: string }[] = [
  { title: "خلاصهٔ یک سند", text: "این سند را خلاصه کن و نکات مهمش را بگو.", description: "از متن‌های طولانی به نکته‌های کلیدی", icon: "document", color: "bg-blue-50 text-blue-600" },
  { title: "پیدا کردن پاسخ", text: "بر اساس اسناد در دسترس، به سؤال من با ذکر منبع پاسخ بده: ", description: "جست‌وجو در دانش و اسناد سازمان", icon: "search", color: "bg-teal-50 text-teal-700" },
  { title: "مرور تصمیم‌ها", text: "تصمیم‌ها و نکات ثبت‌شده در حافظهٔ پروژه را مرور کن.", description: "ادامهٔ مسیر، با حافظهٔ مشترک پروژه", icon: "memory", color: "bg-amber-50 text-amber-700" },
  { title: "بررسی تعهدات", text: "تعهدات، مهلت‌ها و مسئولیت‌های این قرارداد را استخراج کن.", description: "جزئیاتی که نباید از قلم بیفتند", icon: "check", color: "bg-indigo-50 text-indigo-600" },
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
  agentActivities = [],
  isSending = false,
  isUploadingDocument = false,
  isDocumentProcessing = false,
  conversationDocuments = [],
  onStop,
  userName,
}: ChatWindowProps) {
  const [draft, setDraft] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const stickToBottomRef = useRef(true);
  const composerBusy = isSending || (!group && isStreaming) || isLoadingConversation || uploading || isUploadingDocument;
  const sendBlocked = composerBusy || isDocumentProcessing;
  const failedDocuments = conversationDocuments.filter((document) => document.status === "failed");

  // Mention State
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStartIndex, setMentionStartIndex] = useState<number>(-1);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);

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
    if (!area || !stickToBottomRef.current) return;
    area.scrollTo({ top: area.scrollHeight, behavior: "auto" });
  }, [messages, isStreaming, agentActivities]);

  function submit() {
    if (!draft.trim() || sendBlocked) return;
    stickToBottomRef.current = true;
    onSend(draft.trim());
    setDraft("");
    setMentionQuery(null);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing) return;
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
    <div className="flex h-full min-h-0 flex-col">
      <div
        ref={scrollAreaRef}
        onScroll={() => { const area = scrollAreaRef.current; if (area) stickToBottomRef.current = area.scrollHeight - area.scrollTop - area.clientHeight < 100; }}
        role="log"
        aria-live="polite"
        aria-busy={isStreaming || isLoadingConversation}
        className="flex-1 overflow-y-auto overscroll-contain px-4 pt-4 sm:px-8"
      >
        <div className="mx-auto flex min-h-full w-full max-w-[820px] flex-col space-y-3 pb-6">
          {isLoadingConversation ? (
            <div className="m-auto flex items-center gap-3 text-sm text-gray-500">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-gray-800" />
              در حال بارگذاری گفتگو...
            </div>
          ) : messages.length === 0 ? (
            <div className="m-auto w-full max-w-[760px] py-8 sm:py-12">
              <div className="mb-7 flex items-center gap-3 text-[11px] font-medium text-teal-700"><span className="h-px w-8 bg-teal-500" />فضایی برای فکرهای بزرگ‌تر</div>
              <div className="mb-5 flex items-center gap-3"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#142b40] text-teal-300 shadow-lg shadow-slate-200"><OrbitIcon name={group ? "people" : "spark"} className="h-6 w-6" /></span><span className="text-sm text-slate-500">{group ? "هم‌فکری از اینجا شروع می‌شود" : `سلام${userName ? ` ${userName}` : ""}، خوش آمدید`}</span></div>
              <h2 className="text-balance text-[30px] font-bold leading-[1.65] tracking-tight text-[#162e43] sm:text-[40px]">{group ? "یک تیم، یک گفتگوی مشترک." : <>دانش سازمان،<br /><span className="text-teal-700">در جریان گفتگوی شما.</span></>}</h2>
              <p className="mt-4 max-w-xl text-sm leading-8 text-slate-500">
                {group ? `با اعضای پروژه گفتگو کنید. برای کمک گرفتن از دستیار، ${AI_TRIGGER_TOKEN} را در پیام بنویسید.` : "بپرسید، اسناد را بررسی کنید و به تصمیم‌های روشن‌تر برسید. دستیار شما پاسخ را از میان منابع در دسترس پیدا می‌کند."}
              </p>
              {!group && <>
                <div className="mb-3 mt-8 flex items-center justify-between"><p className="text-xs font-medium text-slate-500">از کجا شروع کنیم؟</p><span className="text-[10px] tracking-widest text-slate-400" dir="ltr">EXPLORE YOUR KNOWLEDGE</span></div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {SUGGESTIONS.map((suggestion) => <button key={suggestion.title} type="button" disabled={composerBusy} onClick={() => { setDraft(suggestion.text); textareaRef.current?.focus(); }} className="suggestion-card group flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white/90 p-4 text-right transition duration-200 hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md disabled:opacity-50">
                    <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${suggestion.color}`}><OrbitIcon name={suggestion.icon} className="h-5 w-5" /></span>
                    <span className="min-w-0 flex-1"><span className="block text-[13px] font-semibold text-slate-700">{suggestion.title}</span><span className="mt-1.5 block text-[11px] leading-5 text-slate-500">{suggestion.description}</span></span>
                    <OrbitIcon name="arrow" className="mt-1 h-3.5 w-3.5 text-slate-300 transition group-hover:text-teal-600" />
                  </button>)}
                </div>
              </>}
            </div>
          ) : (
            messages.map((message) => {
              const activity = agentActivities.find((item) => `pending-${item.replyId}` === message.id);
              return <div key={message.id}>
                {(!activity?.status || message.content) && <MessageBubble message={message} isPending={message.id.startsWith("pending-")} senderName={group && message.sender_id ? senderNames[message.sender_id] ?? "عضو پروژه" : undefined} replyPreview={group && message.reply_to_message_id ? messages.find((item) => item.id === message.reply_to_message_id)?.content.slice(0, 90) : undefined} />}
                {activity?.status && <div className="py-2"><AgentActivityBanner status={activity.status} /></div>}
              </div>;
            })
          )}
          {agentActivities.filter((activity) => activity.status && !messages.some((message) => message.id === `pending-${activity.replyId}`)).map((activity) => <AgentActivityBanner key={activity.replyId} status={activity.status!} />)}
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
          {failedDocuments.map((document) => (
            <div key={document.id} role="alert" className="mx-auto w-full max-w-2xl rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-center text-xs leading-6 text-red-700">
              پردازش سند «{document.filename}» ناموفق بود{document.error_message ? `: ${document.error_message}` : "."}
            </div>
          ))}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="relative shrink-0 px-3 pb-3 pt-3 sm:px-8 sm:pb-5"
      >
        {mentionQuery !== null && mentionItems.length > 0 && (
          <MentionDropdown
            items={mentionItems}
            selectedIndex={selectedMentionIndex}
            onSelect={applyMention}
            onClose={() => setMentionQuery(null)}
          />
        )}

        {conversationDocuments.length > 0 && (
          <div className="mx-auto mb-2 flex max-w-3xl flex-wrap items-center gap-2 px-1">
            <span className="text-xs text-gray-500">پیوست‌های این گفتگو:</span>
            {conversationDocuments.map((document) => (
              <span
                key={document.id}
                title={document.error_message ?? undefined}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs ${document.status === "failed" ? "border-red-200 bg-red-50 text-red-700" : document.status === "ready" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-800"}`}
              >
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5 text-brand-600">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6M8 13h8M8 17h6" />
                </svg>
                <span className="max-w-[180px] truncate">{document.filename}</span>
                {document.status === "processing" && <span className="h-3 w-3 animate-spin rounded-full border-2 border-amber-300 border-t-amber-700" aria-label="در حال پردازش" />}
                {document.status === "ready" && <span aria-label="آماده" className="text-emerald-600">✓</span>}
                {document.status === "failed" && <span aria-label="ناموفق" className="text-red-600">!</span>}

              </span>
            ))}
          </div>
        )}

        <div className="mx-auto flex w-full max-w-[820px] items-end gap-2 rounded-[22px] border border-slate-200 bg-white p-3 shadow-[0_8px_32px_-12px_rgba(20,43,64,0.15)] transition focus-within:border-teal-400 focus-within:ring-4 focus-within:ring-teal-50">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={composerBusy || !onUpload}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:opacity-40"
            aria-label="افزودن سند به این گفتگو"
            title="افزودن سند به این گفتگو"
          >
            {uploading || isUploadingDocument ? (
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
              const input = event.currentTarget;
              const file = input.files?.[0];
              if (!file) return;
              setUploadError(null);
              setUploadSuccess(null);
              const ALLOWED = [".pdf", ".docx", ".pptx", ".xlsx", ".txt"];
              const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
              if (!ALLOWED.includes(ext)) {
                setUploadError("فرمت فایل مجاز نیست (فقط PDF، DOCX، PPTX، XLSX یا TXT).");
                input.value = "";
                return;
              }
              if (file.size > 50 * 1024 * 1024) {
                setUploadError("حجم فایل نباید بیشتر از ۵۰ مگابایت باشد.");
                input.value = "";
                return;
              }
              setUploading(true);
              try {
                if (onUpload) {
                  const document = await onUpload(file);
                  if (document.status === "failed") {
                    setUploadError(document.error_message || `پردازش سند «${file.name}» ناموفق بود.`);
                    return;
                  }
                  setUploadSuccess(document.status === "ready"
                    ? `سند «${file.name}» آمادهٔ استفاده در این گفتگو است.`
                    : `سند «${file.name}» بارگذاری شد؛ تا پایان پردازش، ارسال پیام غیرفعال است.`);
                }
                setTimeout(() => setUploadSuccess(null), 5000);
              } catch (err) {
                setUploadError(err instanceof Error ? err.message : "آپلود ناموفق بود.");
              } finally {
                setUploading(false);
                input.value = "";
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
                : conversationDocuments.length > 0
                ? "درباره سند پیوست‌شده بپرسید..."
                : "سؤالتان را بنویسید یا سندی پیوست کنید…"
            }
            value={draft}
            onChange={(e) => handleDraftChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={composerBusy}
          />
          <button
            type={!group && isStreaming ? "button" : "submit"}
            onClick={!group && isStreaming ? onStop : undefined}
            disabled={!group && isStreaming ? false : !draft.trim() || sendBlocked}
            aria-label={!group && isStreaming ? "توقف دریافت پاسخ" : isDocumentProcessing ? "در حال پردازش فایل‌ها" : "ارسال پیام"}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#163b48] text-white transition hover:bg-teal-700 disabled:bg-slate-200 disabled:text-slate-400"
          >
            {!group && isStreaming ? (
              <span className="h-3 w-3 rounded-sm bg-white" />
            ) : (
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="m7 11 5-5 5 5M12 18V6" />
              </svg>
            )}
          </button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] leading-5 text-gray-400">
          {isDocumentProcessing ? "فایل در حال پردازش است؛ پس از آماده‌شدن می‌توانید پیام را ارسال کنید." : "با @ به اسناد اشاره کنید · Enter ارسال · Shift + Enter خط جدید"}
        </p>
      </form>
    </div>
  );
}
