import React from "react";
import { InteractiveReader } from "../../../components/InteractiveReader";
import { BookDoc } from "../../../lib/types";

export default function BookReaderPage({ params }: { params: { bookId: string } }) {
  const book: BookDoc = {
    bookId: params.bookId,
    jobId: "job-demo",
    ownerUid: "studio-user",
    title: "Photosynthesis & Cellular Energy",
    language: "en",
    format: "textbook_lesson",
    readerUrl: `/books/${params.bookId}`,
    video1080pUrl: "/demo/final_1080p.mp4",
    shorts9x16Url: "/demo/short_9x16.mp4",
    srtUrl: "/demo/captions.srt",
    scormZipUrl: "/demo/scorm_package.zip",
    sourcesMdUrl: "/demo/SOURCES.md",
    durationMs: 300000,
    costUsd: 0.48,
    publishedAt: new Date().toISOString(),
  };
  return <InteractiveReader book={book} scenes={[]} />;
}
