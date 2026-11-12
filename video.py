import os, math, subprocess, asyncio, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

W,H,FPS=720,1280,12
VOICE="en-US-GuyNeural"
OUTS=["the-girl-in-room-309-part-1.mp4","the-girl-in-room-309-part-2.mp4"]
PARTS=[
 {"title":"THE GIRL IN ROOM 309","narration":"At 3:07 in the morning, Arjun received a call from his own phone number. He answered. A little girl whispered, Please, don't let him come inside. Arjun asked who she was. She said, I'm you... from tomorrow. The call died. Then three slow knocks came from his bedroom door. A voice outside said, Arjun, open up. It's me. It sounded exactly like him. His phone buzzed. A message from his own number: Whatever happens, do not open the door. The knocking became violent. Arjun looked through the keyhole. The hallway was empty. But he heard breathing behind him. A little girl stood in the corner, holding an old photograph. It showed Arjun beside her, standing in this very room. On the back was a date: twenty years in the future. The girl looked up and whispered, You're not supposed to be alive tonight. Then every light went out.","end":"STAY TUNED FOR PART 2... TO BE CONTINUED.","scenes":["hotel","phone","hall","girl","blackout"]},
 {"title":"THE GIRL IN ROOM 309","narration":"Arjun switched on his phone flashlight. The girl had vanished, but the photograph remained. On its back, he noticed a room number: 309. His phone rang again. The same number. He answered. The girl screamed, He's behind you! Arjun turned. A tall, faceless man stood inches away. He could not move. The stranger pointed toward the mirror. In the reflection, Arjun saw himself smiling, even though his own face was frozen in terror. His reflection raised one finger and wrote on the glass: You died here twenty years ago. Suddenly, the memory returned. A fire in Room 309. Arjun had run inside to save a little girl, but the ceiling collapsed. He had never escaped. The little girl appeared one final time. I'm sorry, she whispered. I tried to warn you. At sunrise, the hotel manager unlocked Room 309. It was empty. No furniture. No phone. Only words on the dusty mirror: ONE MORE ROOM IS AVAILABLE. Downstairs, the reception phone rang. A familiar voice asked, Hello. I'd like to check in. My name is Arjun.","end":"THE END.","scenes":["empty","flashlight","faceless","mirror","fire","dawn"]}
]
def font(n,b=False):
 p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 return ImageFont.truetype(p,n)
def block(d,x,y,w,h,c,edge=(8,8,12)):
 d.rectangle((x,y,x+w,y+h),fill=c,outline=edge,width=3)
 # small top/right bevel gives game-avatar depth
 d.polygon([(x,y),(x+9,y-7),(x+w+9,y-7),(x+w,y)],fill=tuple(min(255,v+22) for v in c))
 d.polygon([(x+w,y),(x+w+9,y-7),(x+w+9,y+h-7),(x+w,y+h)],fill=tuple(max(0,v-22) for v in c))
def avatar(d,cx,cy,kind="arjun",t=0,sc=1):
 if kind=="arjun": skin=(202,151,112); shirt=(32,95,155); pants=(28,34,49); hair=(35,24,19)
 elif kind=="girl": skin=(225,185,151); shirt=(145,28,48); pants=(48,35,48); hair=(20,14,18)
 else: skin=(3,4,7); shirt=(4,5,8); pants=(2,3,6); hair=(0,0,0)
 s=sc
 # body and limbs are deliberately blocky, like a game avatar
 block(d,int(cx-30*s),int(cy-5*s),60*s,78*s,shirt)
 armshift=int(math.sin(t*3)*5*s)
 block(d,int(cx-52*s),int(cy+2*s+armshift),20*s,67*s,shirt)
 block(d,int(cx+32*s),int(cy+2*s-armshift),20*s,67*s,shirt)
 block(d,int(cx-25*s),int(cy+77*s),22*s,75*s,pants)
 block(d,int(cx+3*s),int(cy+77*s),22*s,75*s,pants)
 block(d,int(cx-29*s),int(cy-75*s),58*s,62*s,skin)
 if kind!="faceless":
  d.rectangle((int(cx-30*s),int(cy-79*s),int(cx+30*s),int(cy-62*s)),fill=hair)
  d.rectangle((int(cx-17*s),int(cy-48*s),int(cx-9*s),int(cy-40*s)),fill=(12,12,16))
  d.rectangle((int(cx+9*s),int(cy-48*s),int(cx+17*s),int(cy-40*s)),fill=(12,12,16))
  if kind=="girl":
   d.rectangle((int(cx-35*s),int(cy-82*s),int(cx+35*s),int(cy-72*s)),fill=(18,10,14))
   d.rectangle((int(cx-36*s),int(cy-65*s),int(cx-28*s),int(cy+8*s)),fill=hair)
   d.rectangle((int(cx+28*s),int(cy-65*s),int(cx+36*s),int(cy+8*s)),fill=hair)
 else:
  d.rectangle((int(cx-23*s),int(cy-55*s),int(cx+23*s),int(cy-42*s)),fill=(0,0,0))
def frame(scene,t,part):
 im=Image.new("RGB",(W,H),(5,7,14)); d=ImageDraw.Draw(im)
 for y in range(H):
  v=int(9+18*y/H); d.line((0,y,W,y),fill=(v,v+2,v+12))
 # atmospheric rain and hotel room architecture
 for i in range(55):
  x=(i*139+int(t*25))%W; y=(i*197+int(t*90))%H
  d.line((x,y,x-5,y+27),fill=(27,43,62),width=2)
 d.rectangle((42,145,678,1130),fill=(13,16,25),outline=(72,76,91),width=7)
 d.rectangle((70,180,650,1110),fill=(22,25,35),outline=(40,46,61),width=4)
 d.rectangle((100,210,620,240),fill=(38,34,39))
 d.text((250,165),"ROOM 309",font=font(28,True),fill=(220,220,225))
 if scene in ("hotel","dawn"):
  d.rectangle((115,300,290,650),fill=(6,13,24),outline=(100,110,130),width=5)
  d.line((200,300,200,650),fill=(80,90,105),width=4)
  d.rectangle((340,800,600,860),fill=(35,31,35))
  avatar(d,365,720,"arjun",t,1.05)
  if scene=="dawn":
   d.rectangle((115,300,290,650),fill=(105,77,83)); d.text((185,390),"SUNRISE",font=font(28,True),fill=(255,190,150))
 elif scene=="phone":
  avatar(d,360,720,"arjun",t,1.0)
  d.rounded_rectangle((500,560,610,760),radius=15,fill=(4,8,15),outline=(130,145,160),width=5)
  d.text((510,590),"3:07 AM",font=font(17,True),fill=(220,235,255))
  d.text((510,640),"CALLING",font=font(16,True),fill=(100,220,170))
 elif scene=="hall":
  d.rectangle((190,280,530,1080),fill=(4,5,9),outline=(110,110,120),width=6)
  d.ellipse((342,620,378,656),fill=(190,165,120))
  avatar(d,360,730,"arjun",t,0.9)
 elif scene=="girl":
  avatar(d,500,760,"girl",t,0.95)
  avatar(d,280,760,"arjun",t,0.95)
  d.rectangle((440,840,560,980),fill=(95,70,50),outline=(205,180,140),width=5)
  d.text((452,900),"20 YEARS",font=font(17,True),fill=(255,235,200))
 elif scene=="empty":
  d.rectangle((170,320,550,1050),fill=(9,10,15),outline=(80,85,95),width=5)
  d.text((285,760),"309",font=font(90,True),fill=(100,100,115))
 elif scene=="flashlight":
  avatar(d,340,740,"arjun",t,1.0)
  glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
  gd.ellipse((190,300,650,950),fill=(180,210,255,65))
  im=Image.alpha_composite(im.convert("RGBA"),glow.filter(ImageFilter.GaussianBlur(55))).convert("RGB"); d=ImageDraw.Draw(im)
 elif scene=="faceless":
  avatar(d,265,760,"arjun",t,0.9); avatar(d,500,650,"faceless",t,1.3)
 elif scene=="mirror":
  d.rectangle((360,270,620,1020),fill=(8,11,17),outline=(150,155,165),width=9)
  avatar(d,250,760,"arjun",t,0.9); avatar(d,490,760,"arjun",t,0.9)
  d.text((385,500),"YOU DIED HERE",font=font(24,True),fill=(230,225,225))
  d.text((420,550),"20 YEARS AGO",font=font(20,True),fill=(230,225,225))
 elif scene=="fire":
  for i in range(18):
   x=(i*83+int(t*34))%W; y=650+(i*61)%520
   d.polygon([(x,y+80),(x-24,y+25),(x+4,y-20),(x+30,y+25)],fill=(210,65+(i%3)*30,10))
  avatar(d,350,750,"arjun",t,0.95)
 # top title and bottom captions
 d.rectangle((0,0,W,115),fill=(0,0,0)); d.text((28,35),PARTS[part]["title"],font=font(25,True),fill=(240,240,245))
 # vignette
 overlay=Image.new("L",(W,H),0); od=ImageDraw.Draw(overlay); od.ellipse((-150,-130,W+150,H+150),fill=145)
 im=Image.composite(im,Image.new("RGB",(W,H),(0,0,0)),overlay.filter(ImageFilter.GaussianBlur(90)))
 return im
def make_srt(text,path,duration):
 words=text.split(); chunks=[]; cur=[]
 for word in words:
  cur.append(word)
  if len(cur)>=8: chunks.append(" ".join(cur)); cur=[]
 if cur: chunks.append(" ".join(cur))
 def stamp(sec):
  ms=int((sec-int(sec))*1000); s=int(sec); return f"{s//3600:02}:{(s%3600)//60:02}:{s%60:02},{ms:03}"
 with open(path,"w",encoding="utf-8") as f:
  for i,line in enumerate(chunks):
   a=i*duration/len(chunks); b=(i+1)*duration/len(chunks)
   f.write(f"{i+1}\n{stamp(a)} --> {stamp(b)}\n{line}\n\n")
async def build(i):
 p=PARTS[i]; audio=f"part{i+1}.mp3"; srt=f"part{i+1}.srt"; silent=f"part{i+1}_silent.mp4"
 await edge_tts.Communicate(p["narration"],VOICE,rate="+4%").save(audio)
 make_srt(p["narration"],srt,60)
 cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",silent]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 scenes=p["scenes"]
 try:
  for n in range(FPS*60):
   t=n/FPS; sc=scenes[min(len(scenes)-1,int(t/(60/len(scenes))))]
   proc.stdin.write(frame(sc,t,i).tobytes())
 finally: proc.stdin.close()
 if proc.wait()!=0: raise RuntimeError("Video render failed")
 out=OUTS[i]
 subprocess.run(["ffmpeg","-y","-i",silent,"-i",audio,"-vf",f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=17,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=110'","-map","0:v","-map","1:a","-t","60","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest",out],check=True)
 os.remove(silent); print("Created",out)
async def main():
 for i in range(2): await build(i)
if __name__=="__main__": asyncio.run(main())
