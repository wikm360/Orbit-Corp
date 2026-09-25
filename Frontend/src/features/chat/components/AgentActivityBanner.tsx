import { OrbitIcon } from "@/shared/components/ui/OrbitIcon";
import { agentStatusLabel } from "../lib/agentStatus";
import { AgentStatus } from "../types";

interface AgentActivityBannerProps {
  status: AgentStatus;
}

export function AgentActivityBanner({ status }: AgentActivityBannerProps) {
  return (
    <div role="status" className="inline-flex max-w-full items-center gap-3 rounded-2xl border border-teal-100 bg-teal-50/70 px-4 py-3 text-xs text-teal-700">
      <OrbitIcon name={status.tool?.includes("insight") ? "memory" : status.status === "reading_documents" ? "document" : status.status === "searching" ? "search" : "spark"} className="h-4 w-4" />
      <span>{agentStatusLabel(status)}</span>
      <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-teal-600" />
    </div>
  );
}
