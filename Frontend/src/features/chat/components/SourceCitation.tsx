import { SourceCitation as SourceCitationType } from "../types";

export function SourceCitationList({ sources }: { sources: SourceCitationType[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-col gap-1 border-t border-gray-100 pt-2">
      <span className="text-xs font-medium text-gray-500">منابع:</span>
      {sources.map((source, index) => (
        <div
          key={`${source.document_id}-${source.chunk_index}`}
          className="rounded bg-gray-50 px-2 py-1 text-xs text-gray-600"
        >
          <span className="font-medium">
            [{index + 1}] {source.document_filename}
          </span>
          <p className="mt-0.5 line-clamp-2 text-gray-500">{source.snippet}</p>
        </div>
      ))}
    </div>
  );
}
