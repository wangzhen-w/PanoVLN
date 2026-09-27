#!/usr/bin/env python3
"""Render 4K, 3x, unmasked release clips from originals for finishing in iMovie.
Requires Pillow and an FFmpeg build with zscale. Outputs stay outside Git.
"""
import argparse, io, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--font-dir',type=Path,required=True,help='Contains Geist.ttf')
p.add_argument('--ffmpeg',required=True)
p.add_argument('--art-only',action='store_true')
a=p.parse_args(); OUT=a.output; OUT.mkdir(parents=True,exist_ok=True); FF=a.ffmpeg
W,H=3840,2160
TONE='zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:peak=10:desat=0,zscale=t=bt709:m=bt709:r=tv'
SCENES=[dict(slug='office-tv',folder='PanoVLN_office_tv_set_1',phone='video_20260920_132421.mp4',title='Office',goal='TV',instruction='Walk straight to the glass wall, then turn right\nand stop in front of the large TV set.',duration=71.3,offset=1.,still=36),dict(slug='hallway-carpet',folder='PanoVLN_hallway_carpet_1',phone='video_20260920_155459.mp4',title='Hallway',goal='Red carpet',instruction='Turn left and go straight.\nWalk until you reach the red carpet and stop.',duration=118.4,offset=1.,still=55),dict(slug='campus-chair',folder='PanoVLN_campus_chair_1',phone='video_20260920_164421.mp4',title='Campus',goal='Chair',instruction='Go straight. On the left, there is a brown recliner.\nWalk over there and stop.',duration=137.7,offset=6.1,still=130)]
def font(size,weight=500):
 f=ImageFont.truetype(str(a.font_dir/'Geist.ttf'),size)
 try:f.set_variation_by_axes([weight])
 except (OSError,ValueError):pass
 return f
def text(d,xy,t,size=60,weight=500,fill='white',anchor=None):d.text(xy,t,font=font(size,weight),fill=fill,anchor=anchor,spacing=18)
def run(cmd,log):
 with (OUT/log).open('w') as f:subprocess.run([FF,'-hide_banner','-y',*cmd],stdout=f,stderr=f,check=True)
def frame(path,t,tone=False):
 cmd=[FF,'-v','error','-ss',str(t),'-i',str(path),'-vf',(TONE+',' if tone else '')+'scale=3840:2160:flags=lanczos','-frames:v','1','-threads','1','-f','image2pipe','-c:v','png','-']
 return Image.open(io.BytesIO(subprocess.check_output(cmd))).convert('RGBA')
def gradient(im):
 shade=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(shade)
 for x in range(W):d.line((x,0,x,H),fill=(4,12,24,int(215*(1-x/W)**1.3)))
 return Image.alpha_composite(im,shade)
for n,s in enumerate(SCENES):
 overlay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(overlay)
 # Only compact information layers; the external camera fills the entire 16:9 frame.
 d.rounded_rectangle((64,64,836,226),40,fill=(10,18,28,172),outline=(255,255,255,100),width=2)
 text(d,(108,93),s['title'],68,650);text(d,(790,111),'3×',52,550,anchor='ra')
 # The complete panorama is 1344 x 672, displayed at its original 2:1 ratio.
 d.rounded_rectangle((2368,64,3776,862),34,fill=(12,21,34,208),outline=(255,255,255,155),width=3)
 text(d,(2402,81),'Panoramic observation',44,550)
 d.rounded_rectangle((64,1774,3776,2088),42,fill=(10,18,28,188),outline=(255,255,255,115),width=2)
 text(d,(112,1814),'INSTRUCTION',35,600,fill='#c4d9ef')
 text(d,(112,1877),s['instruction'],63,500)
 text(d,(3704,1814),f'{n+1:02d} / 03',36,550,fill='#c4d9ef',anchor='ra')
 overlay.save(OUT/(s['slug']+'-overlay.png'))
 photo=frame(a.source_root/'realworld'/s['folder']/s['phone'],s['still'],True)
 photo.convert('RGB').resize((1920,1080),Image.Resampling.LANCZOS).save(OUT/(s['slug']+'-still.jpg'),quality=97)
 # Preview with the actual inset at a matching source time, never a generated observation.
 pano_path=a.source_root/'realworld'/s['folder']/'navigation.mp4'
 b=subprocess.check_output([FF,'-v','error','-ss',str(s['still']-s['offset']),'-i',str(pano_path),'-vf','scale=1344:672','-frames:v','1','-threads','1','-f','image2pipe','-c:v','png','-'])
 preview=Image.alpha_composite(photo,overlay);preview.paste(Image.open(io.BytesIO(b)),(2400,158));preview.convert('RGB').resize((1920,1080),Image.Resampling.LANCZOS).save(OUT/(s['slug']+'-preview.jpg'),quality=95)
intro=gradient(frame(a.source_root/'realworld'/SCENES[0]['folder']/SCENES[0]['phone'],36,True));d=ImageDraw.Draw(intro)
text(d,(180,420),'PanoVLN',310,700)
text(d,(190,835),'Towards Effective Panoramic\nVision-and-Language Navigation',86,550)
pill=Image.new('RGBA',(W,H));pd=ImageDraw.Draw(pill);pd.rounded_rectangle((190,1200,1110,1340),70,fill=(245,249,255,45),outline=(255,255,255,145),width=2)
intro=Image.alpha_composite(intro,pill);d=ImageDraw.Draw(intro)
text(d,(250,1232),'Real-world navigation · 3×',52,550)
text(d,(190,1915),'Zhejiang University  ·  The University of Hong Kong',48,450,fill='#e6ebf3')
intro.convert('RGB').save(OUT/'opening.png');intro.convert('RGB').resize((1920,1080),Image.Resampling.LANCZOS).save(OUT/'film-poster.jpg',quality=97)
end=Image.new('RGB',(W,H),'#0c1422');d=ImageDraw.Draw(end)
text(d,(1920,660),'PanoVLN',280,700,anchor='ma');text(d,(1920,1080),'Code, models and data',80,500,anchor='ma');text(d,(1920,1280),'github.com/wangzhen-w/PanoVLN',66,500,fill='#b8d7ff',anchor='ma');end.save(OUT/'closing.png')
manifest={'canvas':[W,H],'fps':30,'speed':3,'layout':'Full 16:9 external camera; complete 2:1 panorama inset; sequential routes','phone_tonemap':TONE,'original_panorama':[1280,640,10],'scenes':SCENES}
(OUT/'film-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if a.art_only:raise SystemExit
ENC=['-an','-c:v','libx264','-preset','fast','-crf','16','-threads','6','-pix_fmt','yuv420p','-r','30','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-map_metadata','-1','-movflags','+faststart']
clips=OUT/'import';clips.mkdir(exist_ok=True)
run(['-loop','1','-framerate','30','-i',str(OUT/'opening.png'),'-vf','fade=t=in:st=0:d=0.45','-t','4',*ENC,str(clips/'01-opening.mp4')],'opening.log')
for n,s in enumerate(SCENES):
 source=a.source_root/'realworld'/s['folder'];duration=s['duration']/3
 fc=f'[0:v]setpts=(PTS-STARTPTS)/3,fps=30,{TONE},scale=3840:2160:flags=lanczos,format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=3[base];[1:v]format=rgba[art];[2:v]setpts=(PTS-STARTPTS)/3,fps=30,scale=1344:672:flags=lanczos,setsar=1[pano];[base][art]overlay=0:0[a];[a][pano]overlay=2400:158:shortest=1,trim=duration={duration}[v]'
 run(['-ss',str(s['offset']),'-i',str(source/s['phone']),'-loop','1','-framerate','30','-i',str(OUT/(s['slug']+'-overlay.png')),'-i',str(source/'navigation.mp4'),'-filter_complex_threads','2','-filter_complex',fc,'-map','[v]','-t',str(duration),*ENC,str(clips/f'{n+2:02d}-{s["slug"]}.mp4')],s['slug']+'.log');print('Rendered',s['slug'],flush=True)
run(['-loop','1','-framerate','30','-i',str(OUT/'closing.png'),'-t','3',*ENC,str(clips/'05-closing.mp4')],'closing.log')
print('READY FOR IMOVIE',flush=True)
