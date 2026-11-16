import argparse
import heapq
import json
import subprocess
from pathlib import Path

try:
    from .highlight_ranker import rank_highlights
except ImportError:
    from highlight_ranker import rank_highlights


def select_speech_dense_window(rows, duration, clip_len):
    """Legacy selector retained for tests/fallback diagnostics; returns (start, count)."""
    if not rows or duration <= 0 or clip_len <= 0:
        return 0.0, 0
    latest = max(0.0, duration - clip_len)
    candidates = {0.0, latest}
    candidates.update(max(0.0, min(float(start), latest)) for start, _, _ in rows)
    best_start, best_score = 0.0, -1
    for start in sorted(candidates):
        score = sum(1 for begin, finish, _ in rows if begin < start + clip_len and finish > start)
        if score > best_score:
            best_start, best_score = start, score
    return best_start, max(0, best_score)


def run(args):
    subprocess.run(args, check=True)


def probe_duration(path):
    value = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(value)


def build_video_filter(caption_path):
    subtitle_file = Path(caption_path).resolve().as_posix().replace(":", r"\\:")
    subtitles = (
        f"subtitles='{subtitle_file}':"
        "force_style='FontName=Arial,FontSize=18,Bold=1,"
        "Outline=2,Shadow=1,Alignment=2,MarginV=120'"
    )
    crop = (
        "crop=w='if(gt(iw/ih,9/16),ih*9/16,iw)':"
        "h='if(gt(iw/ih,9/16),ih,iw*16/9)'"
    )
    return (
        f"{crop},scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,{subtitles}"
    )


def stamp(seconds):
    ms = max(0, int(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default="viceclips-output")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    source = out / "source.mp4"

    run([
        "yt-dlp", "--no-warnings", "--no-playlist", "-f", "bv*+ba/b",
        "--merge-output-format", "mp4", "-o", str(out / "source.%(ext)s"),
        args.url
    ])
    if not source.exists():
        candidates = sorted(out.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
        if not candidates:
            raise RuntimeError("yt-dlp did not create a source video.")
        source = candidates[0]

    duration = probe_duration(source)
    if duration < 12:
        raise RuntimeError("Source video is too short for a useful highlight.")

    audio = out / "audio.wav"
    run(["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(audio)])

    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(audio), vad_filter=True, word_timestamps=True
    )
    rows = []
    for segment in segments:
        for word in segment.words or []:
            value = word.word.strip()
            if value:
                rows.append((float(word.start), float(word.end), value))
    rows.sort(key=lambda row: row[0])
    if not rows:
        raise RuntimeError("No speech detected; cannot build transcript-ranked clips.")

    clip_len = min(35.0, max(12.0, duration))
    highlights = rank_highlights(rows, duration, clip_len=clip_len, max_results=5)
    best = highlights[0]
    best_start = best["start"]
    end = min(duration, best_start + clip_len)

    caption_path = out / "captions.srt"
    active = [
        (max(0.0, start - best_start), min(clip_len, finish - best_start), word)
        for start, finish, word in rows
        if start < end and finish > best_start
    ]
    with caption_path.open("w", encoding="utf-8") as handle:
        for index, (start, finish, word) in enumerate(active, 1):
            handle.write(
                f"{index}\n{stamp(start)} --> {stamp(max(start + 0.08, finish))}\n"
                f"{word}\n\n"
            )

    video = out / "viceclips-private-test.mp4"
    run([
        "ffmpeg", "-y", "-ss", str(best_start), "-i", str(source),
        "-t", str(end - best_start), "-vf", build_video_filter(caption_path),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video)
    ])

    report = {
        "video": str(video),
        "duration": round(end - best_start, 2),
        "start": round(best_start, 2),
        "language": info.language,
        "ai_score": best["score"],
        "ai_hook": best["hook"],
        "ai_reason": best["reason"],
        "ranked_candidates": highlights,
        "selection_method": "Gemini transcript-based highlight ranking",
        "visual_gameplay_analysis": False,
        "publishing": "DISABLED - private review artifact only"
    }
    (out / "highlight-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "upload-metadata.txt").write_text(
        "Suggested title: GTA 6 — best moment (review before use)\n"
        "Description: Edited gaming highlight. Add source credit and verify reuse permission.\n"
        "#GTA6 #GTAVI #Gaming #Shorts\n\n"
        f"Source URL: {args.url}\n"
        f"Selected range: {best_start:.2f}-{end:.2f}s\n"
        f"Gemini score: {best['score']}/100\n"
        f"Hook: {best['hook']}\nReason: {best['reason']}\n"
        "Publishing: DISABLED — private review artifact only.\n",
        encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
