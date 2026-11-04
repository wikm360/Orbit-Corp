"use client";

import { useParams } from "next/navigation";

import { PresentationScreen } from "@/features/volume-reports/screens/PresentationScreen";

export default function VolumeReportPresentationPage() {
  const { id } = useParams<{ id: string }>();
  return <PresentationScreen reportId={id} />;
}
