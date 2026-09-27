#!/usr/bin/env python3
"""Render additional original-source PanoVLN films, preserving complete camera frames."""
import argparse,io,json,re,subprocess,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser(description=__doc__)
for key in ['source-root','output','font','music']:p.add_argument('--'+key,type=Path,required=True)
p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',default='/opt/homebrew/bin/ffprobe')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
TONE='zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:peak=10:desat=0,zscale=t=bt709:m=bt709:r=tv'
CASES=[('real-carpet','Hallway · Red carpet','realworld/PanoVLN_hallway_carpet_1'),('real-chair','Campus · Recliner','realworld/PanoVLN_campus_chair_1'),('real-elevator','Hallway · Elevator','realworld/PanoVLN_hallway_elevator_1'),('real-sofa','Office · Sofa','realworld/PanoVLN_office_sofa_1_perfect'),('real-water','Office · Water dispenser','realworld/PanoVLN_office_water_dispenser_1'),('simulation-03','Bedroom to staircase','r2r/episode_1065'),('simulation-04','Across the bedroom','r2r/episode_358'),('simulation-05','Living room to laundry','rxr/episode_8206'),('simulation-06','Bedroom to shower','rxr/episode_2210')]
def font(size,weight=500):
 f=ImageFont.truetype(str(a.font),size);f.set_variation_by_axes([weight]);return f
def write(d,xy,t,size=40,fill='#eef1fa',weight=500):d.text(xy,t,font=font(size,weight),fill=fill,spacing=12)
def run(args,log):
 with (a.output/log).open('w') as f:subprocess.run([a.ffmpeg,'-hide_banner','-y',*args],stdout=f,stderr=f,check=True)
manifest=[]
for slug,title,folder in CASES:
 real=slug.startswith('real');W,H=(1920,1080) if real else (2560,1440);root=a.source_root/folder
 source=next(root.glob('video_*.mp4')) if real else root/'navigation.mp4'
 meta=json.loads(subprocess.check_output([a.ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(source)]));s=next(s for s in meta['streams'] if s['codec_type']=='video');source_dur=float(meta['format']['duration']);duration=source_dur/3+2.1
 instruction=json.loads((root/'navigation.json').read_text())['instruction'] if real else (root/'instruction.txt').read_text().strip()
 tone=TONE+',' if s.get('color_transfer')=='arib-std-b67' else ''
 filt=tone+f'scale={W}:-2'
 raw=subprocess.check_output([a.ffmpeg,'-v','error','-ss','5','-i',str(source),'-vf',filt,'-frames:v','1','-f','image2pipe','-c:v','png','-']);photo=Image.open(io.BytesIO(raw)).convert('RGBA')
 opening=Image.new('RGBA',(W,H),'#10182c');opening.alpha_composite(photo,(0,(H-photo.height)//2));opening=Image.alpha_composite(opening,Image.new('RGBA',(W,H),(11,17,35,165)));d=ImageDraw.Draw(opening)
 scale=W/1920;write(d,(int(100*scale),int(310*scale)),'PanoVLN',int(130*scale),weight=700);write(d,(int(108*scale),int(500*scale)),title,int(52*scale));write(d,(int(110*scale),int(610*scale)),('Real-world navigation' if real else 'VLN-CE')+' · 3× speed',int(34*scale),fill='#bdcce5')
 op=a.output/(slug+'-intro.png');opening.convert('RGB').save(op)
 panel=Image.new('RGBA',(W,H),(0,0,0,0) if real else '#10182c');d=ImageDraw.Draw(panel)
 if real:
  d.rounded_rectangle((34,30,720,116),22,fill=(19,28,49,215),outline=(230,239,255,110),width=2);write(d,(58,49),title,38,weight=600)
  d.rounded_rectangle((1720,30,1886,110),22,fill=(19,28,49,215),outline=(230,239,255,110),width=2);write(d,(1745,48),'3×',38,weight=600)
  lines=textwrap.wrap(instruction,86);top=H-55-len(lines)*49-28
  d.rounded_rectangle((34,top,1886,1047),24,fill=(19,28,49,224),outline=(230,239,255,110),width=2);write(d,(62,top+18),'\n'.join(lines),36)
 else:
  write(d,(76,60),'PanoVLN',64,weight=650);write(d,(76,153),title,48,weight=600);write(d,(2280,78),'3×',40)
  lines=textwrap.wrap(instruction,132);write(d,(76,240),'\n'.join(lines),32)
 panel_path=a.output/(slug+'-panel.png');panel.save(panel_path)
 if real:
  fc=f'[1:v]setpts=(PTS-STARTPTS)/3,fps=30,{tone}scale={W}:{H},format=yuv420p,setsar=1[cam];[cam][2:v]overlay=0:0:shortest=1[scene];'
  poster=Image.alpha_composite(photo,panel)
 else:
  scaled=photo.resize((2400,round(photo.height*2400/photo.width)));y=max(620,round((H-70-scaled.height)));poster=panel.copy();poster.alpha_composite(scaled,(80,y))
  fc=f'[1:v]setpts=(PTS-STARTPTS)/3,fps=30,scale=2400:-2:flags=lanczos,setsar=1[cam];[2:v][cam]overlay=80:{y}:shortest=1[scene];'
 poster.convert('RGB').resize((1600,900)).save(a.output/(slug+'-poster.jpg'),quality=94)
 fc+='[0:v]format=yuv420p,setsar=1,settb=1/30[op];[scene]format=yuv420p,settb=1/30[sc];[op][sc]xfade=transition=fade:duration=0.4:offset=2.1,format=yuv420p[v]'
 silent=a.output/(slug+'-silent.mp4');final=a.output/(slug+'.mp4')
 if not final.exists():
  run(['-loop','1','-framerate','30','-t','2.5','-i',str(op),'-i',str(source),'-loop','1','-framerate','30','-i',str(panel_path),'-filter_complex_threads','2','-filter_complex',fc,'-map','[v]','-t',str(duration),'-an','-c:v','libx264','-preset','fast','-crf','19','-maxrate','8M','-bufsize','16M','-threads','4','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-map_metadata','-1','-movflags','+faststart',str(silent)],slug+'-render.log')
  af=f'atrim=0:{duration},asetpts=PTS-STARTPTS,afade=t=in:d=1.5,afade=t=out:st={duration-2}:d=2'
  analysis=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(a.music),'-af',af+',loudnorm=I=-25:TP=-3:LRA=20:print_format=json','-f','null','-'],capture_output=True,text=True,check=True);measured=json.loads(re.findall(r'\{\s*"input_i".*?\}',analysis.stderr,re.S)[-1]);gain=-25-float(measured['input_i'])
  run(['-i',str(silent),'-i',str(a.music),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',af+f',volume={gain}dB','-c:a','aac','-b:a','192k','-ar','48000','-t',str(duration),'-map_metadata','-1','-movflags','+faststart',str(final)],slug+'-mix.log')
 manifest.append({'id':slug,'title':title,'kind':'realworld' if real else 'simulation','source':str(source.relative_to(a.source_root)),'instruction':instruction,'source_duration_seconds':source_dur,'duration_seconds':duration,'source_dimensions':[s['width'],s['height']],'source_fps':s['r_frame_rate'],'dimensions':[W,H],'fps':30,'speed':3,'intro_seconds':2.5,'transition_seconds':0.4,'tone_mapping':TONE if tone else None,'music':'Lonely Dance — Vexento','target_loudness_lufs':-25,'file':final.name,'poster':slug+'-poster.jpg'})
 (a.output/'extended-gallery.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');print('Rendered',slug,flush=True)
