"use client";

// This page used to hardcode a BookDoc pointing at /demo/final_1080p.mp4 with
// `scenes={[]}`, so it always showed a demo video that is not in the
// repository. It now fetches the real book.

import React, { useEffect, useState } from "react";
import { InteractiveReader } from "../../../components/InteractiveReader";
import { BookDoc } from "../../../lib/types";
import { ApiError, NotSignedIn, getBook } from "../../../lib/api";
import { watchUser } from "../../../lib/firebase";

export default function BookReaderPage({ params }: { params: { bookId: string } }) {
  const [book, setBook] = useState<BookDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => watchUser((u) => setSignedIn(Boolean(u))), []);

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await getBook(params.bookId);
        if (!cancelled) {
          setBook(res.book);
          setError(null);
        }
      } catch (e) {
        if (cancelled || e instanceof NotSignedIn) return;
        setError(
          e instanceof ApiError
            ? e.status === 403
              ? "This book is not shared with your account."
              : e.status === 404
                ? "No book with this id."
                : `API error ${e.status}: ${e.message}`
            : (e as Error).message,
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [signedIn, params.bookId]);

  const wrap: React.CSSProperties = { maxWidth: 1080, margin: "0 auto", padding: "2rem" };

  if (signedIn === null) return <main style={wrap}>Checking your session…</main>;
  if (!signedIn) return <main style={wrap}>Sign in to read this book.</main>;
  if (error) return <main style={wrap}><p style={{ color: "#b3261e" }}>{error}</p></main>;
  if (!book) return <main style={wrap}>Loading book {params.bookId}…</main>;

  return <InteractiveReader book={book} scenes={[]} />;
}
