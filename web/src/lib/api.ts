"use client";

// The API client. Before this file there was no API call anywhere in web/src:
// the pages hardcoded a job object with costUsd 0.142 and a /demo/ video path,
// so the UI showed the same invented numbers whatever the backend was doing.
//
// Every value rendered by the app must come from here. If a request fails the
// caller shows the error; it never substitutes a placeholder.

import { BookDoc, JobDoc, SceneDoc } from "./types";
import { idToken } from "./firebase";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

export class NotSignedIn extends Error {
  constructor() {
    super("Not signed in");
    this.name = "NotSignedIn";
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set. Add the pm-api URL to web/apphosting.yaml.",
    );
  }
  const token = await idToken();
  if (!token) throw new NotSignedIn();

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    let detail = "";
    try {
      detail = ((await res.json()) as { detail?: string }).detail || "";
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export interface CreateJobInput {
  title: string;
  format: JobDoc["format"];
  language: JobDoc["language"];
  sourceUri: string;
  /** Required for every tier except picture_book: the engine exits without it. */
  brief?: string;
  targetDurationMs?: number;
  costCapUsd?: number;
  manuscriptPreviewText?: string;
}

export async function createJob(
  input: CreateJobInput,
  idempotencyKey: string,
): Promise<{ job: JobDoc }> {
  return request<{ job: JobDoc }>("/v1/jobs", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(input),
  });
}

export async function getJob(jobId: string): Promise<{ job: JobDoc; scenes: SceneDoc[] }> {
  return request<{ job: JobDoc; scenes: SceneDoc[] }>(`/v1/jobs/${encodeURIComponent(jobId)}`);
}

export async function approveJob(jobId: string): Promise<{ job: JobDoc }> {
  return request<{ job: JobDoc }>(`/v1/jobs/${encodeURIComponent(jobId)}/approve`, {
    method: "POST",
  });
}

export async function cancelJob(jobId: string): Promise<{ job: JobDoc }> {
  return request<{ job: JobDoc }>(`/v1/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
}

export async function getBook(bookId: string): Promise<{ book: BookDoc }> {
  return request<{ book: BookDoc }>(`/v1/books/${encodeURIComponent(bookId)}`);
}

/** States in which the server is still working, so the page keeps polling. */
export const LIVE_STATES: ReadonlySet<string> = new Set([
  "queued",
  "ingesting",
  "planning",
  "scripting",
  "synthesizing_voice",
  "illustrating",
  "rendering",
  "critiquing",
  "publishing",
]);
