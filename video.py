import os, subprocess, asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

W,H,FPS,DURATION = 720,1280,24,15
OUT="the-message-came-from-inside.mp4"
VOICE="en-US-GuyNeural"
NARRATION="At 2:13 AM, three knocks came from the front door. I checked the hallway. Nobody was there. Then my phone buzzed. A message from my own number said: Don't open the door. I'm inside. I froze. Because behind me, in the dark, someone was standing."
CAPTIONS=[
 (0,3.5,"2:13 AM. Three knocks at the door."),
 (3.5,6.4,"The hallway was empty."),
 (6.4,10.7,"A message came from MY number:"),
 (10.7,15,"DON'T OPEN THE DOOR. I'M INSIDE.")
]
def font(size,bold=False):
    paths=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def make_frame(t):
    im=Image.new("RGB",(W,H),(5,7,13)); d=ImageDraw.Draw(im)
    # moody blue-black room gradient
    for y in range(H):
        v=int(7+15*(y/H))
        d.line((0,y,W,y),fill=(v,v+2,v+8))
    # rain streaks outside the window
    for i in range(70):
        x=(i*97+int(t*55))%W; y=(i*173+int(t*260))%H
        d.line((x,y,x-5,y+28),fill=(30,43,58),width=2)
    if t<5.5:
        # door and narrow corridor
        d.rectangle((125,180,595,1050),fill=(12,15,22),outline=(75,82,91),width=8)
        d.rectangle((160,215,560,1040),fill=(18,22,30),outline=(39,45,54),width=4)
        d.ellipse((510,630,530,650),fill=(170,145,100))
        d.rectangle((0,0,W,150),fill=(4,6,11))
        title="THREE KNOCKS"
    elif t<10.8:
        # phone glowing in a hand
        glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        gd.ellipse((140,320,580,1000),fill=(20,80,125,65))
        glow=glow.filter(ImageFilter.GaussianBlur(65)); im=Image.alpha_composite(im.convert("RGBA"),glow); d=ImageDraw.Draw(im)
        d.rounded_rectangle((215,230,505,980),radius=38,fill=(2,4,8),outline=(95,110,125),width=8)
        d.rounded_rectangle((235,270,485,940),radius=22,fill=(12,28,43))
        d.rounded_rectangle((260,430,460,690),radius=18,fill=(27,47,63))
        d.text((278,455),"Message",font=font(24,True),fill=(170,210,235))
        d.text((278,505),"From: You",font=font(20),fill=(130,170,195))
        d.text((278,555),"Don't open",font=font(23,True),fill=(240,245,250))
        d.text((278,590),"the door.",font=font(23,True),fill=(240,245,250))
        d.text((278,635),"I'm inside.",font=font(23,True),fill=(255,90,90))
    else:
        # reveal silhouette behind viewer
        d.rectangle((0,0,W,H),fill=(3,4,8))
        # faint doorway
        d.rectangle((150,100,570,1160),fill=(9,12,18),outline=(33,39,49),width=5)
        pulse=int(8+5*(1+__import__('math').sin(t*5)))
        d.ellipse((285,250,435,405),fill=(pulse+8,pulse+8,pulse+12))
        d.polygon([(300,390),(420,390),(505,1090),(215,1090)],fill=(5,6,10))
        d.ellipse((328,320,350,344),fill=(110,135,150))
        d.ellipse((372,320,394,344),fill=(110,135,150))
        # foreground shoulder silhouette
        d.ellipse((40,890,330,1280),fill=(2,3,6))
    # cinematic vignette
    overlay=Image.new("L",(W,H),0); od=ImageDraw.Draw(overlay)
    od.ellipse((-100,-150,W+100,H+150),fill=180)
    overlay=overlay.filter(ImageFilter.GaussianBlur(100))
    dark=Image.new("RGB",(W,H),(0,0,0))
    im=Image.composite(im.convert("RGB"),dark,overlay)
    d=ImageDraw.Draw(im)
    # captions, burned in
    caption=next((c for a,b,c in CAPTIONS if a<=t<b),"")
    if caption:
        box=d.textbbox((0,0),caption,font=font(31,True))
        tw=box[2]-box[0]; x=(W-tw)//2
        d.rounded_rectangle((x-22,1080,x+tw+22,1150),radius=12,fill=(0,0,0))
        d.text((x,1095),caption,font=font(31,True),fill=(245,245,245),stroke_width=1,stroke_fill=(0,0,0))
    return im

async def main():
    await edge_tts.Communicate(NARRATION,VOICE,rate="+3%",volume="+0%").save("voice.mp3")
    cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","silent.mp4"]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for n in range(FPS*DURATION):
            p.stdin.write(make_frame(n/FPS).tobytes())
    finally:
        p.stdin.close()
    if p.wait()!=0: raise RuntimeError("Video rendering failed")
    subprocess.run(["ffmpeg","-y","-i","silent.mp4","-i","voice.mp3","-f","lavfi","-i","anoisesrc=color=pink:amplitude=0.035:sample_rate=44100","-filter_complex","[1:a]volume=1.15[voice];[2:a]lowpass=f=500,volume=0.10[rain];[voice][rain]amix=inputs=2:duration=first:dropout_transition=1[a]","-map","0:v","-map","[a]","-t",str(DURATION),"-c:v","copy","-c:a","aac","-b:a","128k","-shortest",OUT],check=True)
    print("Created",OUT)
if __name__=="__main__": asyncio.run(main())
