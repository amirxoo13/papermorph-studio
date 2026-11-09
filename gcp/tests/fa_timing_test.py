import asyncio, sys, edge_tts

TEXT = ("کوروش بزرگ در سال ۵۵۰ پیش از میلاد شاهنشاهی هخامنشی را "
        "بنیاد گذاشت. او بابل را گرفت؛ آیا مردم شاد بودند؟")

async def run(voice):
    words, audio = [], 0
    c = edge_tts.Communicate(TEXT, voice, rate="-4%", boundary="WordBoundary")
    async for ch in c.stream():
        if ch["type"] == "audio":
            audio += len(ch["data"])
        elif ch["type"] == "WordBoundary":
            words.append((round(ch["offset"] / 1e7, 3), ch["text"]))
    print(f"{voice}: audio_bytes={audio} word_events={len(words)}")
    for t, w in words:
        print(f"  {t:8.3f}  {w}")
    rising = all(words[i][0] <= words[i + 1][0] for i in range(len(words) - 1))
    print(f"{voice}: monotonic={rising}")
    return len(words), audio, rising

ok = True
for v in ["fa-IR-FaridNeural", "fa-IR-DilaraNeural"]:
    n, a, rising = asyncio.run(run(v))
    if n < 10 or a == 0 or not rising:
        ok = False
sys.exit(0 if ok else 1)
