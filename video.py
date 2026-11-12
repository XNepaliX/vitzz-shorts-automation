import os, math, subprocess, asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

W, H, FPS = 720, 1280, 12
VOICE = "en-US-GuyNeural"
OUTS = ["the-girl-in-room-309-part-1.mp4", "the-girl-in-room-309-part-2.mp4"]

PARTS = [
{
"title":"THE GIRL IN ROOM 309",
"narration":"""At 3:07 in the morning, Arjun received a call from his own phone number. He answered. A little girl whispered, Please, don't let him come inside. Arjun asked who she was. She said, I'm you... from tomorrow. The call died. Then three slow knocks came from his bedroom door. A voice outside said, Arjun, open up. It's me. It sounded exactly like him. His phone buzzed. A message from his own number: Whatever happens, do not open the door. The knocking became violent. Arjun looked through the keyhole. The hallway was empty. But he heard breathing behind him. A little girl stood in the corner, holding an old photograph. It showed Arjun beside her, standing in this very room. On the back was a date: twenty years in the future. The girl looked up and whispered, You're not supposed to be alive tonight. Then every light went out.""",
"end":"STAY TUNED FOR PART 2... TO BE CONTINUED.",
"scenes":["rainy_hotel","phone_call","dark_hall","keyhole","girl_photo","blackout"]
},
{
"title":"THE GIRL IN ROOM 309",
"narration":"""Arjun switched on his phone flashlight. The girl had vanished, but the photograph remained. On its back, he noticed a room number: 309. His phone rang again. The same number. He answered. The girl screamed, He's behind you! Arjun turned. A tall, faceless man stood inches away. He could not move. The stranger pointed toward the mirror. In the reflection, Arjun saw himself smiling, even though his own face was frozen in terror. His reflection raised one finger and wrote on the glass: You died here twenty years ago. Suddenly, the memory returned. A fire in Room 309. Arjun had run inside to save a little girl, but the ceiling collapsed. He had never escaped. The little girl appeared one final time. I'm sorry, she whispered. I tried to warn you. At sunrise, the hotel manager unlocked Room 309. It was empty. No furniture. No phone. Only words on the dusty mirror: ONE MORE ROOM IS AVAILABLE. Downstairs, the reception phone rang. A familiar voice asked, Hello. I'd like to check in. My name is Arjun.""",
"end":"THE END.",
"scenes":["empty_room","phone_flash","faceless_man","mirror_reveal","fire_memory","hotel_dawn"]
}
]

def ft(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p,size)

def draw_scene(scene,t,part):
    im=Image.new("RGB",(W,H),(5,7,12))
    d=ImageDraw.Draw(im)
    # subtle rainy blue-black gradient
    for y in range(H):
        q=int(7+13*y/H)
        d.line((0,y,W,y),fill=(q,q+2,q+9))
    # window rain
    for i in range(48):
        x=(i*137+int(t*19))%W
        y=(i*211+int(t*83))%H
        d.line((x,y,x-4,y+24),fill=(30,43,59),width=2)
    if scene in ("rainy_hotel","hotel_dawn"):
        d.rectangle((75,190,645,1090),fill=(10,13,19),outline=(65,72,82),width=7)
        d.rectangle((130,260,590,1080),fill=(16,20,28),outline=(36,43,54),width=4)
        d.rectangle((190,370,530,900),fill=(7,10,16),outline=(42,49,60),width=3)
        d.text((245,220),"ROOM 309",font=ft(34,True),fill=(190,195,202))
        if scene=="hotel_dawn":
            d.rectangle((0,0,W,250),fill=(35,25,29))
            d.text((190,100),"SUNRISE",font=ft(42,True),fill=(180,130,115))
    elif scene in ("phone_call","phone_flash"):
        glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        gd.ellipse((120,300,600,1000),fill=(20,90,150,85))
        glow=glow.filter(ImageFilter.GaussianBlur(70))
        im=Image.alpha_composite(im.convert("RGBA"),glow); d=ImageDraw.Draw(im)
        d.rounded_rectangle((195,220,525,1050),radius=45,fill=(2,4,8),outline=(115,130,145),width=8)
        d.rounded_rectangle((218,270,502,1000),radius=24,fill=(12,29,45))
        d.text((265,390),"INCOMING CALL",font=ft(25,True),fill=(170,205,230))
        d.text((260,465),"UNKNOWN",font=ft(36,True),fill=(245,245,245))
        d.ellipse((265,770,355,860),fill=(40,170,100))
        d.ellipse((385,770,475,860),fill=(185,45,55))
        if scene=="phone_flash":
            d.text((270,570),"3:07 AM",font=ft(32,True),fill=(210,220,230))
    elif scene in ("dark_hall","keyhole","empty_room"):
        d.rectangle((115,130,605,1150),fill=(9,12,18),outline=(60,67,78),width=8)
        d.rectangle((160,180,560,1110),fill=(15,18,26),outline=(35,42,53),width=4)
        if scene=="keyhole":
            d.ellipse((330,580,390,640),fill=(0,0,0),outline=(100,105,115),width=4)
        if scene=="empty_room":
            d.rectangle((230,800,490,830),fill=(30,32,37))
            d.text((250,855),"309",font=ft(55,True),fill=(130,130,140))
    elif scene in ("girl_photo","faceless_man","mirror_reveal","fire_memory"):
        if scene=="girl_photo":
            d.rectangle((150,220,570,950),fill=(32,28,25),outline=(165,150,125),width=8)
            d.rectangle((185,255,535,900),fill=(18,22,27))
            d.ellipse((275,340,385,450),fill=(105,100,95))
            d.polygon([(250,460),(410,460),(465,800),(195,800)],fill=(45,49,55))
            d.text((205,835),"20 YEARS LATER",font=ft(24,True),fill=(220,210,190))
        else:
            d.rectangle((120,130,600,1140),fill=(8,10,16),outline=(45,52,62),width=5)
            cx=360+int(math.sin(t*1.2)*10)
            d.ellipse((cx-75,260,cx+75,430),fill=(2,3,6))
            d.polygon([(cx-90,420),(cx+90,420),(cx+190,1120),(cx-190,1120)],fill=(1,2,4))
            if scene=="mirror_reveal":
                d.rectangle((170,180,550,1040),outline=(120,130,145),width=8)
                d.text((205,570),"YOU DIED HERE",font=ft(30,True),fill=(210,215,220))
                d.text((270,620),"20 YEARS AGO",font=ft(26,True),fill=(210,215,220))
            if scene=="fire_memory":
                for i in range(20):
                    x=(i*73+int(t*30))%W
                    y=700+(i*43)%500
                    d.ellipse((x,y,x+35,y+75),fill=(150,50+(i%3)*25,12))
    # slow zoom illusion through moving dark vignette and scene heading
    vign=Image.new("L",(W,H),0); vd=ImageDraw.Draw(vign)
    vd.ellipse((-120,-150,W+120,H+150),fill=185)
    vign=vign.filter(ImageFilter.GaussianBlur(100))
    im=Image.composite(im.convert("RGB"),Image.new("RGB",(W,H),(0,0,0)),vign)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,120),fill=(0,0,0))
    d.text((34,38),PARTS[part]["title"],font=ft(25,True),fill=(225,225,230))
    if t>54:
        d.rectangle((20,1030,700,1210),fill=(0,0,0))
        msg=PARTS[part]["end"]
        f=ft(30,True); box=d.textbbox((0,0),msg,font=f)
        d.text(((W-(box[2]-box[0]))//2,1090),msg,font=f,fill=(255,255,255))
    return im

async def make_part(i):
    p=PARTS[i]
    base=f"part{i+1}"
    audio=f"{base}.mp3"; srt=f"{base}.srt"; silent=f"{base}_silent.mp4"
    await edge_tts.Communicate(p["narration"],VOICE,rate="+0%",volume="+0%").save(audio,srt)
    # Generate atmospheric visuals, changing scene every ~10 seconds.
    scenes=p["scenes"]
    duration=60
    cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",silent]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for n in range(FPS*duration):
            t=n/FPS
            scene=scenes[min(len(scenes)-1,int(t/(duration/len(scenes))))]
            proc.stdin.write(draw_scene(scene,t,i).tobytes())
    finally:
        proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError("Video frame rendering failed")
    # Captions are burned in; final card remains visible for the final seconds.
    subprocess.run(["ffmpeg","-y","-i",silent,"-i",audio,"-vf",f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=115'","-map","0:v","-map","1:a","-t",str(duration),"-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest",OUTS[i]],check=True)
    os.remove(silent)
    print("Created",OUTS[i])

async def main():
    for i in range(2):
        await make_part(i)

if __name__=="__main__":
    asyncio.run(main())
