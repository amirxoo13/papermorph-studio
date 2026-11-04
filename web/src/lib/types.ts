export type JobState =
  | "queued"
  | "ingesting"
  | "planning"
  | "awaiting_approval"
  | "scripting"
  | "synthesizing_voice"
  | "illustrating"
  | "rendering"
  | "critiquing"
  | "publishing"
  | "done"
  | "failed"
  | "paused_budget"
  | "cancelled";

export type ContentFormat = "textbook_lesson" | "picture_book" | "documentary_shorts";
export type LanguageCode = "en" | "fa";

export interface WordTiming {
  word: string;
  startMs: number;
  endMs: number;
  confidence: number;
}

export interface LicenceEntry {
  assetId: string;
  assetType: string;
  uri: string;
  licenceSpdx: string;
  attribution: string;
  verified: boolean;
}

export interface SceneDoc {
  sceneId: string;
  jobId: string;
  index: number;
  title: string;
  narrationText: string;
  targetDurationMs: number;
  actualDurationMs?: number;
  visualPrompt: string;
  svgOverlaySpec?: string;
  audioUri?: string;
  imageUri?: string;
  videoShardUris: string[];
  wordTimings: WordTiming[];
  citations: string[];
  status: string;
}

export interface JobDoc {
  jobId: string;
  ownerUid: string;
  title: string;
  format: ContentFormat;
  language: LanguageCode;
  stylePresetId: string;
  sourceUri: string;
  state: JobState;
  requireApproval: boolean;
  approvedAt?: string;
  targetDurationMs: number;
  actualDurationMs?: number;
  costUsd: number;
  costCapUsd: number;
  tokensIn: number;
  tokensOut: number;
  stageAttempts: Record<string, number>;
  artifacts: Record<string, string>;
  licences: LicenceEntry[];
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
}

export interface BookDoc {
  bookId: string;
  jobId: string;
  ownerUid: string;
  title: string;
  language: LanguageCode;
  format: ContentFormat;
  readerUrl: string;
  video1080pUrl: string;
  shorts9x16Url?: string;
  srtUrl: string;
  scormZipUrl?: string;
  sourcesMdUrl: string;
  durationMs: number;
  costUsd: number;
  publishedAt: string;
}
