"use client";

import { useParams } from "next/navigation";

import { ReportDetailScreen } from "@/features/volume-reports/screens/ReportDetailScreen";

export default function VolumeReportPage() {
  const { id } = useParams<{ id: string }>();
  return <ReportDetailScreen reportId={id} />;
}
