import json, subprocess, sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file() or path.stat().st_size < 100_000:
    raise SystemExit("FAIL: output MP4 is missing or too small")
raw = subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries",
    "format=duration:stream=codec_type,width,height",
    "-of", "json", str(path)
], text=True)
data = json.loads(raw)
duration = float(data.get("format", {}).get("duration", 0))
video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
if not video or not audio:
    raise SystemExit("FAIL: video or audio stream is missing")
w, h = int(video["width"]), int(video["height"])
if h <= w or abs((w / h) - (9 / 16)) > 0.01:
    raise SystemExit(f"FAIL: expected vertical 9:16 video, got {w}x{h}")
if duration < 45 or duration > 65:
    raise SystemExit(f"FAIL: expected 45–65 seconds, got {duration:.1f}s")
print(f"PASS: {w}x{h}, {duration:.1f}s, video + audio present, {path.stat().st_size} bytes")
