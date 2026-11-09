"use client";

// This page used to render a hardcoded `placeholderJob` with costUsd 0.142,
// so it showed the same invented figures no matter what the backend held.
// It now fetches the real job and shows nothing it did not receive.

import React, { useCallback, useEffect, useState } from "react";
import { StageTimeline } from "../../../components/StageTimeline";
import { JobDoc, SceneDoc } from "../../../lib/types";
import { ApiError, LIVE_STATES, NotSignedIn, approveJob, getJob } from "../../../lib/api";
import { watchUser } from "../../../lib/firebase";

const POLL_MS = 5000;

export default function JobDetailPage({ params }: { params: { jobId: string } }) {
  const [job, setJob] = useState<JobDoc | null>(null);
  const [scenes, setScenes] = useState<SceneDoc[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => watchUser((u) => setSignedIn(Boolean(u))), []);

  const load = useCallback(async () => {
    try {
      const res = await getJob(params.jobId);
      setJob(res.job);
      setScenes(res.scenes || []);
      setError(null);
    } catch (e) {
      if (e instanceof NotSignedIn) {
        setError(null);
      } else if (e instanceof ApiError) {
        setError(
          e.status === 403
            ? "This job belongs to another account."
            : e.status === 404
              ? "No job with this id."
              : `API error ${e.status}: ${e.message}`,
        );
      } else {
        setError((e as Error).message);
      }
    }
  }, [params.jobId]);

  useEffect(() => {
    if (!signedIn) return;
    void load();
  }, [signedIn, load]);

  // Keep polling only while the server is still working on it.
  useEffect(() => {
    if (!signedIn || !job || !LIVE_STATES.has(job.state)) return;
    const t = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(t);
  }, [signedIn, job, load]);

  const onApprove = async () => {
    setApproving(true);
    try {
      const res = await approveJob(params.jobId);
      setJob(res.job);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setApproving(false);
    }
  };

  const wrap: React.CSSProperties = { maxWidth: 1080, margin: "0 auto", padding: "2rem" };

  if (signedIn === null) return <main style={wrap}>Checking your session…</main>;
  if (!signedIn) return <main style={wrap}>Sign in to see this job.</main>;
  if (error) return <main style={wrap}><p style={{ color: "#b3261e" }}>{error}</p></main>;
  if (!job) return <main style={wrap}>Loading job {params.jobId}…</main>;

  return (
    <main style={wrap}>
      <StageTimeline job={job} />
      {job.state === "awaiting_approval" && (
        <button onClick={onApprove} disabled={approving} style={{ marginTop: "1.5rem" }}>
          {approving ? "Sending…" : "Approve and continue"}
        </button>
      )}
      {scenes.length > 0 && (
        <section style={{ marginTop: "2rem" }}>
          <h2>Scenes ({scenes.length})</h2>
          <ol>
            {scenes.map((s) => (
              <li key={s.sceneId}>{s.title}</li>
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}
