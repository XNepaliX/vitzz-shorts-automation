import bpy, math, os, sys, subprocess, asyncio
from mathutils import Vector
import edge_tts

W,H,FPS=540,960,10
DUR=60
OUT=os.getcwd()
def mat(name,color,metal=0,rough=.6,emission=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 bs=m.node_tree.nodes.get("Principled BSDF"); bs.inputs["Base Color"].default_value=(*color,1); bs.inputs["Metallic"].default_value=metal; bs.inputs["Roughness"].default_value=rough
 if emission:
  bs.inputs["Emission Color"].default_value=(*color,1); bs.inputs["Emission Strength"].default_value=emission
 return m
def cube(name,loc,scale,ma, bevel=.08):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma)
 if bevel:
  mod=o.modifiers.new("soft_edges","BEVEL"); mod.width=bevel; mod.segments=3
  o.modifiers.new("weighted_normals","WEIGHTED_NORMAL")
 return o
def sphere(name,loc,scale,ma):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; o.data.materials.append(ma); bpy.ops.object.shade_smooth(); return o
def animate(o,frames):
 for f,loc in frames: o.location=loc; o.keyframe_insert(data_path="location",frame=f)
def character(prefix,x,y,z,coat,skin,hair,faceless=False):
 parts=[]
 torso=cube(prefix+"_torso",(x,y,z+1.15),(.72,.42,.95),coat,.12); parts.append(torso)
 head=sphere(prefix+"_head",(x,y,z+1.95),(.31,.3,.34),skin); parts.append(head)
 if not faceless:
  sphere(prefix+"_hair",(x,y-.02,z+2.15),(.33,.31,.18),hair)
  for ex in [-.11,.11]: sphere(prefix+"_eye",(x+ex,y-.285,z+1.99),(.035,.02,.045),mat("eye_black",(0.01,.01,.02)))
 for side in [-1,1]:
  arm=cube(prefix+"_arm",(x+side*.48,y,z+1.2),(.2,.24,.78),coat,.09); parts.append(arm)
  leg=cube(prefix+"_leg",(x+side*.2,y,z+.42),(.25,.3,.78),mat(prefix+"_pants",(.06,.08,.13)),.07); parts.append(leg)
 # parent to torso for simple full-body motion
 for p in parts:
  if p!=torso: p.parent=torso; p.matrix_parent_inverse=torso.matrix_world.inverted()
 return torso
def setup(part):
 bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
 bpy.context.scene.render.engine="BLENDER_EEVEE_NEXT"
 sc=bpy.context.scene; sc.render.resolution_x=W; sc.render.resolution_y=H; sc.render.resolution_percentage=100
 sc.render.fps=FPS; sc.frame_start=1; sc.frame_end=DUR*FPS
 sc.render.image_settings.file_format="PNG"; sc.render.image_settings.color_mode="RGB"
 sc.view_settings.view_transform="AgX"
 # dark hotel suite
 wall=mat("blue charcoal walls",(.025,.035,.06)); floor=mat("polished floor",(.045,.05,.07),.35,.3)
 wood=mat("dark wood",(.12,.065,.045)); metal=mat("aged brass",(.28,.19,.08),.75,.25)
 skin=mat("warm skin",(.55,.32,.21)); hair=mat("dark hair",(.018,.012,.015)); blue=mat("jacket",(.035,.11,.22)); red=mat("dress",(.22,.025,.055))
 cube("floor",(0,0,-.2),(8,9,.3),floor)
 cube("back_wall",(0,3.6,2.6),(8,.25,5.5),wall)
 cube("left_wall",(-4,0,2.6),(.25,7,5.5),wall)
 # hotel door and brass number
 cube("room_309_door",(0,3.42,1.65),(1.8,.12,3.2),wood)
 cube("door inset",(0,3.33,1.7),(1.55,.04,2.8),mat("door panel",(.07,.035,.03)))
 cube("room plaque",(0,3.28,3.25),(.65,.05,.22),metal)
 # bed / window / mirror
 cube("bed base",(2,-.5,.35),(2.1,2.7,.55),wood)
 cube("mattress",(2,-.5,.72),(2.05,2.65,.28),mat("linen",(.17,.18,.21)))
 cube("window frame",(-2.2,3.4,2.5),(1.5,.15,2.2),metal)
 cube("window night",(-2.2,3.29,2.5),(1.32,.05,2.02),mat("night",(.008,.02,.055),emission=.25))
 cube("mirror frame",(3.25,1.5,2.1),(.12,1.4,2.5),metal)
 mirror=cube("mirror glass",(3.17,1.5,2.1),(.04,1.22,2.3),mat("mirror",(.035,.06,.08),.8,.12))
 arjun=character("Arjun",-1.0,-.7,0,blue,skin,hair)
 girl=character("Girl",2.0,-.1,0,red,skin,mat("girl hair",(.01,.008,.012)))
 faceless=character("Visitor",0,1.8,0,mat("black suit",(.004,.006,.01)),mat("void",(.001,.001,.002)),hair,True)
 phone=cube("glowing phone",(-.45,-.65,1.65),(.16,.06,.3),mat("phone glow",(.05,.55,.8),.2,.2,2))
 # camera and dramatic lights
 bpy.ops.object.camera_add(location=(0,-8,3.0)); cam=bpy.context.object; cam.name="cinematic_camera"
 def aim(obj,p): obj.rotation_euler=(Vector(p)-obj.location).to_track_quat("-Z","Y").to_euler()
 aim(cam,(0,.7,1.35)); cam.data.lens=38; sc.camera=cam
 def light(name,loc,power,color,size):
  bpy.ops.object.light_add(type="AREA",location=loc); l=bpy.context.object; l.name=name; l.data.energy=power; l.data.color=color; l.data.shape="DISK"; l.data.size=size; aim(l,(0,0,1)); return l
 light("cold moonlight",(-3,-1,4),500,(.25,.42,1),4)
 light("warm practical",(2,2,3.7),220,(1,.35,.15),2)
 light("door rim",(0,3,4),350,(.3,.55,1),2)
 # staged character blocking and camera push-ins
 if part==1:
  animate(arjun,[(1,(-1,-.7,0)),(180,(-.8,-.7,0)),(360,(-.25,-.8,0)),(600,(-.8,-.7,0))])
  animate(girl,[(1,(2,-.1,0)),(300,(2,-.1,0)),(420,(.8,-.6,0)),(550,(.8,-.6,0)),(600,(2,-.1,0))])
  animate(faceless,[(1,(0,1.8,0)),(430,(0,1.8,0)),(520,(0,.6,0)),(600,(0,.6,0))])
 else:
  animate(arjun,[(1,(-.8,-.7,0)),(160,(-.3,-.8,0)),(360,(-1,-.7,0)),(600,(-1,-.7,0))])
  animate(faceless,[(1,(0,1.8,0)),(100,(0,.7,0)),(350,(0,.3,0)),(600,(0,.3,0))])
  animate(girl,[(1,(2,-.1,0)),(390,(2,-.1,0)),(450,(1,-.4,0)),(500,(2,-.1,0)),(600,(2,-.1,0))])
 # camera animation
 cam.location=(0,-8,3.0); cam.keyframe_insert(data_path="location",frame=1)
 cam.location=(.25,-6.8,2.6); cam.keyframe_insert(data_path="location",frame=180)
 cam.location=(-.25,-7.3,2.9); cam.keyframe_insert(data_path="location",frame=360)
 cam.location=(0,-6.1,2.5); cam.keyframe_insert(data_path="location",frame=600)
 # animate phone pulse and mirror highlight
 for f,s in [(1,1),(30,1.18),(60,1),(90,1.18),(120,1)]:
  phone.scale=(s,s,s); phone.keyframe_insert(data_path="scale",frame=f)
 sc.render.filepath=os.path.join(OUT,f"raw{part}.mp4"); sc.render.image_settings.file_format="FFMPEG"; sc.render.ffmpeg.format="MPEG4"; sc.render.ffmpeg.codec="H264"; sc.render.ffmpeg.constant_rate_factor="MEDIUM"; sc.render.ffmpeg.ffmpeg_preset="GOOD"
 return sc
STORIES=[
 ("At 3:07 in the morning, Arjun received a call from his own phone number. He answered. A little girl whispered, Please, don't let him come inside. Arjun asked who she was. She said, I'm you, from tomorrow. The call died. Three slow knocks came from his bedroom door. A voice outside said, Arjun, open up. It's me. It sounded exactly like him. His phone buzzed. A message from his own number: Whatever happens, do not open the door. The knocking became violent. Arjun looked through the keyhole. The hallway was empty. But he heard breathing behind him. A little girl stood in the corner, holding an old photograph. It showed Arjun beside her, standing in this very room. On the back was a date, twenty years in the future. The girl looked up and whispered, You're not supposed to be alive tonight. Then every light went out.", "STAY TUNED FOR PART 2. TO BE CONTINUED."),
 ("Arjun switched on his phone flashlight. The girl had vanished, but the photograph remained. On its back, he noticed a room number: 309. His phone rang again. The same number. He answered. The girl screamed, He's behind you! Arjun turned. A tall, faceless man stood inches away. He could not move. The stranger pointed toward the mirror. In the reflection, Arjun saw himself smiling, even though his own face was frozen in terror. His reflection raised one finger and wrote on the glass: You died here twenty years ago. Suddenly, the memory returned. A fire in Room 309. Arjun had run inside to save a little girl, but the ceiling collapsed. He had never escaped. The little girl appeared one final time. I'm sorry, she whispered. I tried to warn you. At sunrise, the hotel manager unlocked Room 309. It was empty. No furniture. No phone. Only words on the dusty mirror: ONE MORE ROOM IS AVAILABLE. Downstairs, the reception phone rang. A familiar voice asked, Hello. I'd like to check in. My name is Arjun.", "THE END.")
]
async def audio(part):
 txt,end=STORIES[part-1]; voice="en-US-GuyNeural"
 await edge_tts.Communicate(txt+" "+end,voice,rate="-2%",volume="+0%").save(f"voice{part}.mp3")
def srt(part):
 txt,end=STORIES[part-1]; words=(txt+" "+end).split(); chunks=[" ".join(words[i:i+8]) for i in range(0,len(words),8)]
 def stamp(s):
  ms=int((s-int(s))*1000); n=int(s); return f"{n//3600:02}:{(n%3600)//60:02}:{n%60:02},{ms:03}"
 with open(f"cap{part}.srt","w") as f:
  for i,c in enumerate(chunks):
   a=i*DUR/len(chunks); b=(i+1)*DUR/len(chunks)
   f.write(f"{i+1}\n{stamp(a)} --> {stamp(b)}\n{c}\n\n")
def main():
 part=int(os.environ["PART"]); sc=setup(part); bpy.ops.render.render(animation=True)
 asyncio.run(audio(part)); srt(part)
 subprocess.run(["ffmpeg","-y","-i",f"raw{part}.mp4","-i",f"voice{part}.mp3","-vf",f"subtitles=cap{part}.srt:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=85'","-t","60","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",f"the-girl-in-room-309-part-{part}.mp4"],check=True)
if __name__=="__main__": main()
