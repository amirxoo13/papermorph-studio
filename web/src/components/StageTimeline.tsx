import React from "react";
import { JobDoc, JobState } from "../lib/types";

const ORDERED_STAGES: JobState[] = [
  "queued",
  "ingesting",
  "planning",
  "awaiting_approval",
  "scripting",
  "synthesizing_voice",
  "illustrating",
  "rendering",
  "critiquing",
  "publishing",
  "done",
];

export interface StageTimelineProps {
  job: JobDoc;
  onApprove?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
}

export const StageTimeline: React.FC<StageTimelineProps> = ({
  job,
  onApprove,
  onCancel,
}) => {
  const pct = Math.min(100, Math.round((job.costUsd / job.costCapUsd) * 100));
  return (
    <section aria-label="Job Stage Timeline and Budget Meter" style={{ padding: "1.5rem", border: "1px solid #264653", borderRadius: 12 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>{job.title}</h2>
        <span>State: <strong>{job.state}</strong></span>
      </header>
      <div style={{ marginTop: "1rem" }}>
        <div>Cost Guard: ${job.costUsd.toFixed(4)} / ${job.costCapUsd.toFixed(2)} ({pct}%)</div>
        <progress value={job.costUsd} max={job.costCapUsd} style={{ width: "100%" }} />
      </div>
      <ol style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", listStyle: "none", padding: 0, marginTop: "1rem" }}>
        {ORDERED_STAGES.map((st) => {
          const isCurrent = job.state === st;
          return (
            <li
              key={st}
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: 6,
                background: isCurrent ? "#2a9d8f" : "#e9ecef",
                color: isCurrent ? "#fff" : "#264653",
                fontWeight: isCurrent ? 700 : 400,
              }}
            >
              {st}
            </li>
          );
        })}
      </ol>
      {job.state === "awaiting_approval" && onApprove && (
        <button onClick={() => onApprove(job.jobId)} style={{ marginRight: "0.75rem", padding: "0.5rem 1rem", background: "#2a9d8f", color: "#fff" }}>
          Approve Storyboard & Resume Pipeline
        </button>
      )}
      {job.state !== "done" && job.state !== "cancelled" && onCancel && (
        <button onClick={() => onCancel(job.jobId)} style={{ padding: "0.5rem 1rem", background: "#e76f51", color: "#fff" }}>
          Cancel Job
        </button>
      )}
    </section>
  );
};
