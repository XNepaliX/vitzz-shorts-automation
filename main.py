import asyncio
import math
import os
import random
import re
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
FRAMES = OUT / "frames"
OUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)

WIDTH, HEIGHT, FPS, DURATION = 720, 1280, 12, 60
FRAME_COUNT = FPS * DURATION
topic = os.getenv("SHORT_TOPIC", "What your brain does while you sleep").strip()
script = os.getenv("SHORT_SCRIPT", "").strip() or (
    "Your brain does not simply switch off when you fall asleep. "
    "While your body rests, your brain stays busy sorting information from the day. "
    "Some memories are strengthened, while less important details may fade. "
    "During deep sleep, the brain helps stabilize facts and skills you have practiced. "
    "Dreaming can happen in several sleep stages, especially during REM sleep, when brain activity becomes more active. "
    "Sleep also supports attention, mood, and learning the next day. "
    "That is why staying up all night before an exam can backfire. "
    "A good night's sleep is not wasted time. It is part of how your brain learns. "
    "So tonight, give your brain the rest it needs."
)

def run(cmd):
    subprocess.run(cmd, check=True)

def load_font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = f"/usr/share/fonts/truetype/dejavu/{name}"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

TITLE = load_font(43, True)
LABEL = load_font(23, True)
SMALL = load_font(18)
CAPTION_STYLE = (
    "FontName=DejaVu Sans,FontSize=20,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
    "BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=150"
)

async def make_voice():
    communicate = edge_tts.Communicate(
        script,
        voice=os.getenv("VOICE", "en-US-GuyNeural"),
        rate=os.getenv("VOICE_RATE", "+3%"),
    )
    await communicate.save(str(OUT / "voiceover.mp3"))

def timestamp(seconds):
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def make_captions():
    audio_duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(OUT / "voiceover.mp3")
    ], text=True).strip())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
    weights = [max(1, len(s.split())) for s in sentences]
    total = sum(weights)
    # Captions are mapped across the actual narration, and never exceed the film.
    cursor = 0.0
    rows = []
    for i, (sentence, weight) in enumerate(zip(sentences, weights), 1):
        end = audio_duration if i == len(sentences) else cursor + audio_duration * weight / total
        rows.append(f"{i}\n{timestamp(cursor)} --> {timestamp(end)}\n{sentence}\n")
        cursor = end
    (OUT / "captions.srt").write_text("\n".join(rows), encoding="utf-8")
    return audio_duration

def lerp(a, b, t):
    return a + (b - a) * t

def draw_brain(draw, cx, cy, t, scale=1.0):
    # Original vector-style brain illustration with pulsing neural pathways.
    pulse = 1.0 + 0.035 * math.sin(t * 2.2)
    s = scale * pulse
    left = (cx - 105*s, cy - 95*s, cx + 8*s, cy + 100*s)
    right = (cx - 8*s, cy - 95*s, cx + 105*s, cy + 100*s)
    draw.ellipse(left, fill=(105, 118, 255), outline=(210, 220, 255), width=4)
    draw.ellipse(right, fill=(160, 105, 255), outline=(225, 210, 255), width=4)
    # folds
    for k in range(4):
        yy = cy - 55*s + k*36*s
        draw.arc((cx-90*s, yy-18*s, cx+5*s, yy+25*s), 185, 350, fill=(225,230,255), width=3)
        draw.arc((cx-5*s, yy-18*s, cx+90*s, yy+25*s), 190, 355, fill=(240,220,255), width=3)
    draw.line((cx, cy-85*s, cx, cy+90*s), fill=(40,45,105), width=max(2, int(4*s)))
    nodes = []
    for i in range(9):
        angle = t*0.65 + i*math.tau/9
        nx = cx + math.cos(angle)*145*s
        ny = cy + math.sin(angle)*125*s
        nodes.append((nx, ny))
        draw.line((cx, cy, nx, ny), fill=(75, 220, 255), width=2)
        r = 7 + 2*math.sin(t*3+i)
        draw.ellipse((nx-r, ny-r, nx+r, ny+r), fill=(120, 245, 255))
    draw.ellipse((cx-12*s, cy-12*s, cx+12*s, cy+12*s), fill=(255,255,255))

def draw_scene(frame_index):
    t = frame_index / FPS
    scene = min(4, int(t // 12))
    local = (t - scene*12) / 12
    palettes = [
        ((7, 12, 38), (30, 22, 82)),
        ((8, 20, 48), (15, 70, 105)),
        ((23, 12, 55), (72, 30, 105)),
        ((5, 30, 55), (15, 75, 95)),
        ((12, 15, 48), (48, 35, 95)),
    ]
    top, bottom = palettes[scene]
    img = Image.new("RGB", (WIDTH, HEIGHT))
    px = img.load()
    for y in range(HEIGHT):
        f = y / (HEIGHT-1)
        c = tuple(int(lerp(top[i], bottom[i], f)) for i in range(3))
        for x in range(WIDTH):
            px[x, y] = c
    d = ImageDraw.Draw(img, "RGBA")

    # Floating stars / particles move continuously between frames.
    rng = random.Random(41)
    for i in range(48):
        bx = rng.randint(0, WIDTH)
        by = rng.randint(0, HEIGHT)
        speed = 8 + (i % 7) * 3
        x = (bx + math.sin(t*0.4+i)*22) % WIDTH
        y = (by - t*speed) % HEIGHT
        radius = 1 + (i % 3)
        alpha = 70 + int(80*(0.5+0.5*math.sin(t*2+i)))
        d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(160,220,255,alpha))

    titles = [
        "YOUR BRAIN NEVER CLOCKS OUT",
        "IT SORTS THE DAY'S MEMORIES",
        "SLEEP HAS DIFFERENT STAGES",
        "REST HELPS YOU LEARN",
        "SLEEP IS BRAIN WORK",
    ]
    tags = ["THE SURPRISING TRUTH", "MEMORY CONSOLIDATION", "DEEP SLEEP + REM", "FOCUS • MOOD • LEARNING", "GIVE YOUR BRAIN A BREAK"]
    title = titles[scene]
    d.rounded_rectangle((34, 62, WIDTH-34, 150), radius=24, fill=(4, 9, 28, 165), outline=(100,210,255,170), width=2)
    d.text((WIDTH//2, 106), tags[scene], font=SMALL, fill=(110,225,255), anchor="mm")
    # Wrap headline into two centered lines if necessary.
    words = title.split()
    lines, line = [], ""
    for word in words:
        test = (line+" "+word).strip()
        if d.textbbox((0,0), test, font=TITLE)[2] > WIDTH-90:
            lines.append(line); line = word
        else:
            line = test
    if line: lines.append(line)
    y = 190
    for text_line in lines[:2]:
        d.text((WIDTH//2, y), text_line, font=TITLE, fill=(255,255,255), anchor="mt",
               stroke_width=1, stroke_fill=(35,40,95))
        y += 58

    # Scene-specific animated illustrations.
    if scene in (0, 1, 3, 4):
        cx = int(WIDTH/2 + math.sin(t*0.7)*18)
        cy = 650 + int(math.sin(t*1.4)*12)
        draw_brain(d, cx, cy, t, 1.0 if scene != 4 else 0.92)
    else:
        # A moon, stars and orbiting sleep-stage rings.
        cx, cy = WIDTH//2, 635
        for radius in (115, 165, 215):
            d.arc((cx-radius, cy-radius, cx+radius, cy+radius),
                  int(t*25)%360, int(t*25)%360+250, fill=(120,205,255,120), width=3)
        d.ellipse((cx-80, cy-80, cx+80, cy+80), fill=(255,225,150,255))
        d.ellipse((cx-35, cy-100, cx+100, cy+35), fill=(23,18,68,255))
        for i in range(7):
            a = t*0.6+i*math.tau/7
            x, y = cx+math.cos(a)*185, cy+math.sin(a)*185
            d.ellipse((x-6,y-6,x+6,y+6), fill=(130,235,255,220))

    # Progress line makes the film feel like one continuous explainer.
    d.rounded_rectangle((50, 1045, WIDTH-50, 1057), radius=6, fill=(255,255,255,45))
    d.rounded_rectangle((50, 1045, 50+(WIDTH-100)*(t/DURATION), 1057),
                        radius=6, fill=(95,225,255,230))
    d.text((WIDTH//2, 1115), "FACTS THAT MAKE YOU THINK", font=SMALL,
           fill=(205,220,255,210), anchor="mm")
    return img.convert("RGB")

def make_frames():
    for i in range(FRAME_COUNT):
        draw_scene(i).save(FRAMES / f"frame_{i:05d}.jpg", quality=88)

def render_video():
    subtitle_path = str((OUT / "captions.srt").resolve())
    frames_pattern = str((FRAMES / "frame_%05d.jpg").resolve())
    video_path = OUT / "short.mp4"
    run([
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", frames_pattern,
        "-i", str(OUT / "voiceover.mp3"),
        "-vf", f"scale=1080:1920:flags=lanczos,subtitles='{subtitle_path}':force_style='{CAPTION_STYLE}'",
        "-t", str(DURATION), "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", "-shortest", str(video_path)
    ])
    # If narration is shorter than 60 seconds, pad the soundtrack with silence
    # while keeping the full animated 60-second explainer intact.
    actual = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ], text=True).strip())
    if actual < DURATION - 0.25:
        run([
            "ffmpeg", "-y", "-i", str(video_path), "-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100", "-map", "0:v:0",
            "-map", "0:a:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-af", "apad=pad_dur=60", "-t", "60", "-shortest",
            str(OUT / "short-padded.mp4")
        ])
        (OUT / "short-padded.mp4").replace(video_path)
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height",
        "-of", "json", str(video_path)
    ], text=True)
    print("Verified 60-second vertical video:", probe)
    if not video_path.is_file() or video_path.stat().st_size < 100_000:
        raise RuntimeError("Video output is missing or unexpectedly small")

if __name__ == "__main__":
    asyncio.run(make_voice())
    make_captions()
    make_frames()
    render_video()
