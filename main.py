import os
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import asyncio

OUT = Path("output")
OUT.mkdir(exist_ok=True)

topic = os.getenv("SHORT_TOPIC", "A strange fact about the human brain").strip()
script = os.getenv("SHORT_SCRIPT", "").strip() or (
    f"Here's a surprising fact about {topic.lower()}. "
    "Your brain is constantly processing information, even when you are resting. "
    "Follow vitzz for more interesting facts."
)

def run(cmd):
    subprocess.run(cmd, check=True)

async def make_voice():
    communicate = edge_tts.Communicate(
        script,
        voice=os.getenv("VOICE", "en-US-GuyNeural"),
        rate=os.getenv("VOICE_RATE", "+8%"),
    )
    await communicate.save(str(OUT / "voiceover.mp3"))

def timestamp(seconds):
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def make_captions():
    # Create readable phrase-level captions. Timing is distributed over the
    # measured narration duration so a subtitle file is always produced.
    duration_text = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(OUT / "voiceover.mp3")
    ], text=True).strip()
    total_duration = float(duration_text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
    if not sentences:
        sentences = [script]
    weights = [max(1, len(s.split())) for s in sentences]
    total_words = sum(weights)
    cursor = 0.0
    entries = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights), start=1):
        start = cursor
        end = total_duration if index == len(sentences) else cursor + total_duration * weight / total_words
        entries.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{sentence}\n")
        cursor = end
    (OUT / "captions.srt").write_text("\n".join(entries), encoding="utf-8")

def make_visual():
    img = Image.new("RGB", (1080, 1920), (12, 18, 38))
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 76)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 43)
        brand_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except OSError:
        title_font = body_font = brand_font = ImageFont.load_default()

    draw.rounded_rectangle((70, 180, 1010, 1710), radius=55, fill=(24, 35, 68), outline=(65, 190, 255), width=5)
    draw.text((110, 280), "DID YOU KNOW?", font=brand_font, fill=(75, 210, 255))
    words = topic.upper().split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=title_font)[2] > 820:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    y = 500
    for item in lines[:5]:
        draw.text((110, y), item, font=title_font, fill="white")
        y += 105
    draw.rounded_rectangle((110, 1510, 970, 1660), radius=35, fill=(10, 15, 32))
    draw.text((150, 1550), "VITZZ", font=body_font, fill="white")
    img.save(OUT / "visual.png")

def render_video():
    subtitle_path = str((OUT / "captions.srt").resolve())
    # FFmpeg filter paths need escaped colons on Windows; runner is Ubuntu.
    style = "FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=180"
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(OUT / "visual.png"),
        "-i", str(OUT / "voiceover.mp3"), "-c:v", "libx264",
        "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-vf",
        f"scale=1080:1920,fps=30,subtitles='{subtitle_path}':force_style='{style}'",
        "-shortest", str(OUT / "vitzz-short.mp4")
    ])
    (OUT / "script.txt").write_text(script, encoding="utf-8")
    if not (OUT / "vitzz-short.mp4").is_file() or (OUT / "vitzz-short.mp4").stat().st_size == 0:
        raise RuntimeError("Video output was not created")
    print("Created captioned video:", OUT / "vitzz-short.mp4")

if __name__ == "__main__":
    asyncio.run(make_voice())
    make_captions()
    make_visual()
    render_video()
