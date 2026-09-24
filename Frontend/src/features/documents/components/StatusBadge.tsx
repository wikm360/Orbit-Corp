import { Badge } from "@/shared/components/ui/Badge";

import { DocumentStatus } from "../types";

const STATUS_CONFIG: Record<DocumentStatus, { label: string; tone: "gray" | "green" | "red" }> = {
  processing: { label: "در حال پردازش", tone: "gray" },
  ready: { label: "آماده", tone: "green" },
  failed: { label: "ناموفق", tone: "red" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge tone={config.tone}>
      <span className="inline-flex items-center gap-1.5">
        {status === "processing" && (
          <span className="inline-block h-1.5 w-1.5 animate-ping rounded-full bg-amber-500" />
        )}
        {config.label}
      </span>
    </Badge>
  );
}
