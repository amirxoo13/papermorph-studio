import React, { useState } from "react";
import { BookDoc, SceneDoc } from "../lib/types";

export interface InteractiveReaderProps {
  book: BookDoc;
  scenes: SceneDoc[];
}

export const InteractiveReader: React.FC<InteractiveReaderProps> = ({ book, scenes }) => {
  const [currentMs, setCurrentMs] = useState<number>(0);
  const isRtl = book.language === "fa";

  return (
    <article
      dir={isRtl ? "rtl" : "ltr"}
      lang={book.language}
      style={{
        fontFamily: isRtl ? "'Vazirmatn', sans-serif" : "'Inter', sans-serif",
        maxWidth: 1080,
        margin: "0 auto",
        padding: "2rem",
      }}
    >
      <header style={{ borderBottom: "2px solid #264653", paddingBottom: "1rem", marginBottom: "1.5rem" }}>
        <h1>{book.title}</h1>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <a href={book.video1080pUrl}>Download 1080p MP4</a>
          {book.shorts9x16Url && <a href={book.shorts9x16Url}>Download 9:16 Vertical Short</a>}
          <a href={book.srtUrl}>Download Subtitles (.srt)</a>
          {book.scormZipUrl && <a href={book.scormZipUrl}>Download SCORM 1.2 Package</a>}
          <a href={book.sourcesMdUrl}>View SPDX Licence Ledger (SOURCES.md)</a>
        </div>
      </header>

      <section aria-label="Synchronized Video Player" style={{ marginBottom: "2rem" }}>
        <video
          src={book.video1080pUrl}
          controls
          style={{ width: "100%", borderRadius: 12, background: "#000" }}
          onTimeUpdate={(e) => setCurrentMs(Math.floor(e.currentTarget.currentTime * 1000))}
        >
          <track kind="captions" src={book.srtUrl} srcLang={book.language} default />
        </video>
      </section>

      <section aria-label="Synchronized Interactive Pages">
        {scenes.map((scene) => (
          <div key={scene.sceneId} style={{ padding: "1.25rem", marginBottom: "1rem", borderRadius: 8, background: "#f8f5ee" }}>
            <h3>{scene.title}</h3>
            <p style={{ lineHeight: 1.8, fontSize: "1.15rem" }}>
              {scene.wordTimings.length > 0
                ? scene.wordTimings.map((wt, idx) => {
                    const active = currentMs >= wt.startMs && currentMs <= wt.endMs;
                    return (
                      <span
                        key={`${scene.sceneId}-w-${idx}`}
                        style={{
                          backgroundColor: active ? "#e76f51" : "transparent",
                          color: active ? "#ffffff" : "#264653",
                          padding: "0 0.2rem",
                          borderRadius: 4,
                        }}
                      >
                        {wt.word}{" "}
                      </span>
                    );
                  })
                : scene.narrationText}
            </p>
          </div>
        ))}
      </section>
    </article>
  );
};
