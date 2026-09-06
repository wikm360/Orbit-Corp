import { Markdown } from "@/shared/components/ui/Markdown";

import { ChatMessage } from "../types";
import { SourceCitationList } from "./SourceCitation";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-lg bg-brand-600 px-4 py-2 text-sm text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-lg bg-white px-4 py-2 text-sm text-gray-900 shadow-sm">
        {message.content ? <Markdown content={message.content} /> : "..."}
        <SourceCitationList sources={message.sources} />
      </div>
    </div>
  );
}
