import { Badge } from "@/shared/components/ui/Badge";

import { DocumentStatus } from "../types";

const STATUS_CONFIG: Record<DocumentStatus, { label: string; tone: "gray" | "green" | "red" }> = {
  processing: { label: "در حال پردازش", tone: "gray" },
  ready: { label: "آماده", tone: "green" },
  failed: { label: "ناموفق", tone: "red" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge tone={config.tone}>{config.label}</Badge>;
}
