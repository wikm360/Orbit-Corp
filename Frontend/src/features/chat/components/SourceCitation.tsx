import { SourceCitation as SourceCitationType } from "../types";

export function SourceCitationList({ sources }: { sources: SourceCitationType[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-4 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <span className="text-xs font-semibold text-gray-500">منابع پاسخ</span>
      {sources.map((source, index) => (
        <div
          key={`${source.document_id}-${source.chunk_index}`}
          className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-xs leading-5 text-gray-600"
        >
          <span className="font-medium">
            [{index + 1}] {source.document_filename}
          </span>
          <p className="mt-1 line-clamp-2 text-gray-500">{source.snippet}</p>
        </div>
      ))}
    </div>
  );
}
