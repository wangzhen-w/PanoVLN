#!/usr/bin/env python3
"""Render the release film from original recordings. Requires Pillow and FFmpeg with zscale."""
import argparse
from pathlib import Path
import subprocess,io,json,textwrap,concurrent.futures,shutil
from PIL import Image,ImageDraw,ImageFont
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path, required=True, help='Directory containing realworld/')
parser.add_argument('--output', type=Path, required=True, help='Working/master directory outside the repository')
parser.add_argument('--font-dir', type=Path, required=True, help='Contains Geist.ttf and GildaDisplay.ttf from Google Fonts')
parser.add_argument('--ffmpeg', required=True, help='FFmpeg build with zscale, tonemap and libx264')
args=parser.parse_args()
ROOT=args.source_root; OUT=args.output; FONT_DIR=args.font_dir; FF=args.ffmpeg
OUT.mkdir(parents=True, exist_ok=True)
W,H=3840,2160; BG='#FFF8F0'; INK='#321C22'; WINE='#63252F'; MUTED='#64555B'
TONE='zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:peak=10:desat=0,zscale=t=bt709:m=bt709:r=tv'
SCENES=[dict(slug='office-tv',folder='PanoVLN_office_tv_set_1',phone='video_20260920_132421.mp4',title='Office · TV',instruction='Walk straight to the glass wall, then turn right and stop in front of the large TV set.',duration=71.3,offset=1.0,still=36),dict(slug='hallway-carpet',folder='PanoVLN_hallway_carpet_1',phone='video_20260920_155459.mp4',title='Hallway · Red carpet',instruction='Turn left and go straight. Walk until you reach the red carpet and stop.',duration=118.4,offset=1.0,still=55),dict(slug='campus-chair',folder='PanoVLN_campus_chair_1',phone='video_20260920_164421.mp4',title='Campus · Chair',instruction='Go straight. On the left, there is a brown recliner. Walk over there and stop.',duration=137.7,offset=6.1,still=130)]
def font(size,serif=False): return ImageFont.truetype(str(FONT_DIR/('GildaDisplay.ttf' if serif else 'Geist.ttf')),size)
def txt(d,xy,t,size,color=INK,serif=False,anchor=None): d.text(xy,t,font=font(size,serif),fill=color,anchor=anchor)
def run(args,log):
 with open(OUT/log,'w') as f: subprocess.run([FF,'-hide_banner','-y',*args],stdout=f,stderr=f,check=True)
def still(path,t,scale):
 b=subprocess.check_output([FF,'-v','error','-ss',str(t),'-i',str(path),'-vf',TONE+',scale='+scale,'-frames:v','1','-threads','1','-f','image2pipe','-c:v','png','-']);return Image.open(io.BytesIO(b)).convert('RGB')
def caption(d,s,y=1740):
 words=s.split(); lines=[];line='';f=font(66)
 for word in words:
  new=(line+' '+word).strip()
  if d.textlength(new,font=f)>3520: lines.append(line);line=word
  else: line=new
 lines.append(line)
 for n,line in enumerate(lines):txt(d,(112,y+n*94),line,66)
for n,s in enumerate(SCENES):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
 txt(d,(96,66),'PanoVLN',64,WINE);txt(d,(3744,76),f'{n+1:02d} / 03',52,MUTED,anchor='ra')
 d.line((96,188,3744,188),fill='#DCCFCD',width=2)
 txt(d,(96,226),s['title'],134,serif=True);txt(d,(3744,268),'3× playback',54,WINE,anchor='ra')
 txt(d,(96,444),'First-person panorama',54);txt(d,(1944,444),'Third-person view',54)
 txt(d,(112,1634),'Navigation instruction',46,WINE);caption(d,s['instruction'])
 d.line((96,2050,3744,2050),fill='#DCCFCD',width=2)
 for j,name in enumerate(['Office · TV','Hallway · Red carpet','Campus · Chair']):
  x=96+j*1250; d.line((x,2050,min(x+1120,3744),2050),fill=WINE if j==n else '#DCCFCD',width=8 if j==n else 2);txt(d,(x,2080),name,42,WINE if j==n else MUTED)
 im.save(OUT/(s['slug']+'-canvas.png'))
 photo=still(ROOT/'realworld'/s['folder']/s['phone'],s['still'],'1216:684');photo.save(OUT/(s['slug']+'-still.jpg'),quality=96)
intro=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(intro)
txt(d,(1920,150),'PanoVLN',320,WINE,True,'ma')
txt(d,(1920,560),'Towards Effective Panoramic',90,INK,True,'ma');txt(d,(1920,680),'Vision-and-Language Navigation',90,INK,True,'ma')
for i,s in enumerate(SCENES):
 intro.paste(Image.open(OUT/(s['slug']+'-still.jpg')),(72+i*1236,980));txt(d,(72+i*1236,1700),s['title'],58)
txt(d,(1920,1950),'Real-world navigation · 3× playback',62,WINE,anchor='ma')
intro.save(OUT/'opening.png')
intro.resize((1920,1080),Image.Resampling.LANCZOS).save(OUT/'film-poster.jpg',quality=96)
end=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(end);txt(d,(1920,620),'PanoVLN',300,WINE,True,'ma');txt(d,(1920,1120),'Code, models and data',80,INK,True,'ma');txt(d,(1920,1290),'github.com/wangzhen-w/PanoVLN',66,WINE,anchor='ma');end.save(OUT/'closing.png')
ENC=['-an','-c:v','libx264','-preset','fast','-crf','16','-threads','4','-pix_fmt','yuv420p','-r','30','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-map_metadata','-1','-movflags','+faststart']
def render_scene(s):
 source=ROOT/'realworld'/s['folder'];duration=s['duration']/3
 # Both recordings run at exactly 3x. Retain a phone's final frame when it ends before the panoramic recorder.
 fc=f'[0:v]setpts=PTS-STARTPTS,format=yuv420p[bg];[1:v]setpts=(PTS-STARTPTS)/3,fps=30,scale=1800:900:flags=lanczos,setsar=1[p];[2:v]setpts=(PTS-STARTPTS)/3,fps=30,{TONE},scale=1800:1012:flags=lanczos,format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=3[e];[bg][p]overlay=96:586[a];[a][e]overlay=1944:530:shortest=1,trim=duration={duration}[v]'
 run(['-loop','1','-framerate','30','-i',str(OUT/(s['slug']+'-canvas.png')),'-i',str(source/'navigation.mp4'),'-ss',str(s['offset']),'-i',str(source/s['phone']),'-filter_complex_threads','2','-filter_complex',fc,'-map','[v]','-t',str(duration),*ENC,str(OUT/(s['slug']+'.mp4'))],s['slug']+'.log');print('Rendered',s['slug'],flush=True)
# Opening uses a brief fade; the navigation sequences remain uninterrupted.
run(['-loop','1','-framerate','30','-i',str(OUT/'opening.png'),'-vf','fade=t=in:st=0:d=0.4:color=0xFFF8F0','-t','4',*ENC,str(OUT/'opening.mp4')],'opening.log')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(render_scene,SCENES))
run(['-loop','1','-framerate','30','-i',str(OUT/'closing.png'),'-t','3',*ENC,str(OUT/'closing.mp4')],'closing.log')
segments=['opening',*(s['slug'] for s in SCENES),'closing'];(OUT/'concat.txt').write_text(''.join("file '"+str(OUT/(x+'.mp4'))+"'\n" for x in segments))
run(['-f','concat','-safe','0','-i',str(OUT/'concat.txt'),'-c','copy','-bsf:v','h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0','-map_metadata','-1','-movflags','+faststart',str(OUT/'PanoVLN_navigation_release.mp4')],'concat.log')
(OUT/'film-source-manifest.json').write_text(json.dumps({'master':'PanoVLN_navigation_release.mp4','canvas':[W,H],'fps':30,'speed':3,'phone_tonemap':TONE,'original_panorama':[1280,640,10],'scenes':SCENES},indent=2)+'\n')
print('FILM READY',flush=True)
