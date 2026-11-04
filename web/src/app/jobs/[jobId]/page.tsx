import React from "react";
import { StageTimeline } from "../../../components/StageTimeline";
import { JobDoc } from "../../../lib/types";

export default function JobDetailPage({ params }: { params: { jobId: string } }) {
  const placeholderJob: JobDoc = {
    jobId: params.jobId,
    ownerUid: "studio-user",
    title: "Papermorph Job Monitor",
    format: "textbook_lesson",
    language: "en",
    stylePresetId: "default-editorial",
    sourceUri: "gs://gen-lang-client-0484425781-pm-raw-uploads/manuscript.pdf",
    state: "awaiting_approval",
    requireApproval: true,
    targetDurationMs: 300000,
    costUsd: 0.142,
    costCapUsd: 5.0,
    tokensIn: 1450,
    tokensOut: 3120,
    stageAttempts: { ingesting: 1, planning: 1 },
    artifacts: {},
    licences: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "2rem" }}>
      <StageTimeline job={placeholderJob} />
    </main>
  );
}
