import { KeyboardEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/shared/components/ui/Button";

import { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  onSend: (text: string) => void;
}

const MAX_TEXTAREA_HEIGHT_PX = 200;

export function ChatWindow({ messages, isStreaming, error, onSend }: ChatWindowProps) {
  const [draft, setDraft] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [draft]);

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
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-gray-400">
            سوال خود را درباره اسناد سازمان یا هر موضوع دیگری بپرسید.
          </p>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-end gap-2 border-t border-gray-200 p-4"
      >
        <textarea
          ref={textareaRef}
          rows={1}
          className="flex-1 resize-none overflow-y-auto rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          style={{ maxHeight: MAX_TEXTAREA_HEIGHT_PX }}
          placeholder="پیام خود را بنویسید... (Enter برای ارسال، Shift+Enter برای خط جدید)"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />
        <Button type="submit" isLoading={isStreaming}>
          ارسال
        </Button>
      </form>
    </div>
  );
}
