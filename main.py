import asyncio
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import edge_tts

OUT = Path("output")
OUT.mkdir(exist_ok=True)

topic = os.getenv("SHORT_TOPIC", "A strange fact about the human brain").strip()
script = os.getenv("SHORT_SCRIPT", "").strip() or (
    f"Here's a surprising fact about {topic.lower()}. "
    "Your brain is constantly processing information, even when you are resting. "
    "Follow vitzz for more interesting facts."
)

async def make_voice():
    communicate = edge_tts.Communicate(script, voice="en-US-GuyNeural", rate="+8%")
    await communicate.save(str(OUT / "voiceover.mp3"))

def make_visual():
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), (12, 18, 38))
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 76)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 43)
        brand_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except OSError:
        title_font = body_font = brand_font = ImageFont.load_default()

    draw.rounded_rectangle((70, 250, 1010, 1660), radius=55, fill=(24, 35, 68), outline=(65, 190, 255), width=5)
    draw.text((110, 340), "DID YOU KNOW?", font=brand_font, fill=(75, 210, 255))
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
    y = 560
    for item in lines[:5]:
        draw.text((110, y), item, font=title_font, fill="white")
        y += 105

    draw.rounded_rectangle((110, 1200, 970, 1450), radius=35, fill=(10, 15, 32))
    draw.text((150, 1270), "FOLLOW FOR MORE", font=brand_font, fill=(75, 210, 255))
    draw.text((150, 1350), "VITZZ  •  @vitzzzz-p9v", font=body_font, fill="white")
    img.save(OUT / "visual.png")

def render_video():
    audio = OUT / "voiceover.mp3"
    image = OUT / "visual.png"
    video = OUT / "vitzz-short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
        "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest",
        "-vf", "scale=1080:1920,fps=30", str(video)
    ], check=True)
    (OUT / "script.txt").write_text(script, encoding="utf-8")
    print(f"Created {video}")

if __name__ == "__main__":
    asyncio.run(make_voice())
    make_visual()
    render_video()
