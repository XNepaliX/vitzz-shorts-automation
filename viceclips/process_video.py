import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel

def run(args):
    subprocess.run(args, check=True)

def probe_duration(path):
    value = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(value)

def stamp(seconds):
    ms = max(0, int(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--output", default="viceclips-output")
    a = p.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    source = out / "source.mp4"

    run(["yt-dlp", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
         "-o", str(source), a.url])
    if not source.exists():
        candidates = list(out.glob("source.*"))
        if not candidates:
            raise RuntimeError("yt-dlp did not create a source video")
        source = candidates[0]

    duration = probe_duration(source)
    if duration < 12:
        raise RuntimeError("Source video is too short for a useful highlight")

    audio = out / "audio.wav"
    run(["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
         str(audio)])

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio), vad_filter=True, word_timestamps=True)
    rows = []
    for seg in segments:
        words = seg.words or []
        for w in words:
            if w.word.strip():
                rows.append((float(w.start), float(w.end), w.word.strip()))
    if not rows:
        raise RuntimeError("No speech was detected; cannot create captioned clip")

    clip_len = min(35.0, max(12.0, duration))
    # Choose the 35-second interval with the most recognized words.
    candidates = [max(0.0, min(duration - clip_len, t - clip_len / 2))
                  for t, _, _ in rows]
    candidates += [0.0, max(0.0, duration - clip_len)]
    best_start, best_score = 0.0, -1
    for start in candidates:
        score = sum(1 for s, e, _ in rows if s < start + clip_len and e > start)
        if score > best_score:
            best_start, best_score = start, score
    end = min(duration, best_start + clip_len)

    caption_path = out / "captions.srt"
    active = [(max(0, s-best_start), min(clip_len, e-best_start), w)
              for s, e, w in rows if s < end and e > best_start]
    with caption_path.open("w", encoding="utf-8") as f:
        for i, (s, e, word) in enumerate(active, 1):
            f.write(f"{i}\n{stamp(s)} --> {stamp(max(s+0.08,e))}\n{word}\n\n")

    video = out / "viceclips-private-test.mp4"
    subtitle_filter = "subtitles=captions.srt:force_style='FontName=Arial,FontSize=18,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=120'"
    run(["ffmpeg", "-y", "-ss", str(best_start), "-i", str(source), "-t", str(end-best_start),
         "-vf", f"crop='if(gt(iw/ih,9/16),ih*9/16,iw)':'if(gt(iw/ih,9/16),ih,iw*16/9)',"
                f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,{subtitle_filter}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(video)])

    metadata = out / "upload-metadata.txt"
    metadata.write_text(
        "Suggested title: GTA 6 — best moment (review before use)\n"
        "Description: Edited highlight. Add source credit and verify reuse permission.\n"
        "#GTA6 #GTAVI #Gaming #Shorts\n\n"
        f"Source URL: {a.url}\nSelected range: {best_start:.2f}s–{end:.2f}s\n"
        "Publishing: DISABLED — private test artifact only.\n",
        encoding="utf-8")
    print(json.dumps({"video": str(video), "duration": end-best_start,
                      "start": best_start, "speech_words": best_score,
                      "language": info.language}, indent=2))

if __name__ == "__main__":
    main()
