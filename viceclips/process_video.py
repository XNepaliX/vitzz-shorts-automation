import argparse
import bisect
import json
import subprocess
from pathlib import Path

try:
    from .highlight_ranker import rank_highlights
except ImportError:
    from highlight_ranker import rank_highlights


def select_speech_dense_window(rows, duration, clip_len):
    """Legacy diagnostic selector; score candidate windows in O(n log n)."""
    if not rows or duration <= 0 or clip_len <= 0:
        return 0.0, 0
    latest = max(0.0, duration - clip_len)
    starts = sorted(float(s) for s, _, _ in rows)
    ends = sorted(float(e) for _, e, _ in rows)
    candidates = {0.0, latest}
    candidates.update(max(0.0, min(latest, float(s) - clip_len / 2)) for s, _, _ in rows)
    best_start, best_score = 0.0, -1
    for start in candidates:
        score = bisect.bisect_left(starts, start + clip_len) - bisect.bisect_right(ends, start)
        if score > best_score or (score == best_score and start < best_start):
            best_start, best_score = start, score
    return best_start, max(0, best_score)


def run(command):
    subprocess.run(command, check=True)


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
        "force_style='FontName=Arial,FontSize=18,Bold=1,Outline=2,"
        "Shadow=1,Alignment=2,MarginV=120'"
    )
    crop = ("crop=w='if(gt(iw/ih,9/16),ih*9/16,iw)':"
            "h='if(gt(iw/ih,9/16),ih,iw*16/9)'")
    return f"{crop},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,{subtitles}"


def stamp(seconds):
    ms = max(0, int(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Video URL that yt-dlp can access; direct MP4 URLs are supported.")
    parser.add_argument("--output", default="viceclips-output")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    run(["yt-dlp", "--no-warnings", "--no-playlist", "--retries", "3",
         "--fragment-retries", "3", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
         "-o", str(out / "source.%(ext)s"), args.url])
    candidates = sorted(out.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not candidates:
        raise RuntimeError("No source file downloaded. For YouTube bot checks, supply an authorized direct MP4 download URL.")
    source = candidates[0]
    duration = probe_duration(source)
    if duration < 12:
        raise RuntimeError("Source video is too short for a useful highlight.")
    audio = out / "audio.wav"
    run(["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio), vad_filter=True, word_timestamps=True)
    rows = [(float(w.start), float(w.end), w.word.strip())
            for seg in segments for w in (seg.words or []) if w.word.strip()]
    rows.sort(key=lambda row: row[0])
    if not rows:
        raise RuntimeError("No speech detected; transcript-based highlight ranking cannot run.")
    clip_len = min(35.0, max(12.0, duration))
    highlights = rank_highlights(rows, duration, clip_len=clip_len, max_results=5)
    best = highlights[0]
    start, end = best["start"], min(duration, best["start"] + clip_len)
    captions = out / "captions.srt"
    active = [(max(0.0, s-start), min(clip_len, e-start), word)
              for s, e, word in rows if s < end and e > start]
    with captions.open("w", encoding="utf-8") as f:
        for i, (s, e, word) in enumerate(active, 1):
            f.write(f"{i}\n{stamp(s)} --> {stamp(max(s+0.08,e))}\n{word}\n\n")
    video = out / "viceclips-private-test.mp4"
    run(["ffmpeg", "-y", "-ss", str(start), "-i", str(source), "-t", str(end-start),
         "-vf", build_video_filter(captions), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video)])
    report = {"video": str(video), "duration": round(end-start, 2), "start": round(start, 2),
              "language": info.language, "ai_provider": best["provider"], "ai_score": best["score"],
              "ai_hook": best["hook"], "ai_reason": best["reason"],
              "ranked_candidates": highlights, "selection_method": best["provider"] + " transcript-based ranking",
              "visual_gameplay_analysis": False, "publishing": "DISABLED - private review only"}
    (out / "highlight-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "upload-metadata.txt").write_text(
        f"Suggested title: GTA gameplay highlight (review before use)\n"
        f"Selected range: {start:.2f}-{end:.2f}s\n"
        f"Provider: {best['provider']} | Score: {best['score']}/100\n"
        f"Hook: {best['hook']}\nReason: {best['reason']}\n"
        "Publishing: DISABLED — private review only.\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
