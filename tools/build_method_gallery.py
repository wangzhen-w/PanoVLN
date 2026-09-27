#!/usr/bin/env python3
"""Build five standalone 3x method films from original external-camera recordings.

Requires Pillow, Geist.ttf, and FFmpeg with zscale/tonemap/libx264. The full camera
frame is preserved. Music is supplied separately and must be cleared for use.
"""
import argparse,io,json,math,re,subprocess,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--font',type=Path,required=True);p.add_argument('--music',type=Path,required=True)
p.add_argument('--ffmpeg',default='/opt/homebrew/bin/ffmpeg');p.add_argument('--ffprobe',default='/opt/homebrew/bin/ffprobe')
a=p.parse_args();a.output.mkdir(exist_ok=True,parents=True)
W,H=1920,1080
TONE='zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:peak=10:desat=0,zscale=t=bt709:m=bt709:r=tv'
METHODS=[('panovln','PanoVLN','PanoVLN_office_tv_1'),('navid','NaVid','NaVid_office_tv_1'),('navila','NaVILA','NaVILA_office_tv_2'),('streamvln','StreamVLN','StreamVLN_office_tv_1'),('janusvln','JanusVLN','JanusVLN_office_tv_1')]
instruction='Walk straight to the glass wall, then turn right and stop in front of the large TV set.'
def font(size,weight=500):
 f=ImageFont.truetype(str(a.font),size);f.set_variation_by_axes([weight]);return f
def text(d,xy,t,size,weight=500,fill='#17283e'):
 d.text(xy,t,font=font(size,weight),fill=fill,spacing=10)
def run(args,log):
 with (a.output/log).open('w') as f:subprocess.run([a.ffmpeg,'-hide_banner','-y',*args],stdout=f,stderr=f,check=True)
manifest=[]
for slug,name,folder in METHODS:
 path=next(x for x in (a.source_root/'realworld/supplement'/folder).glob('video_*.mp4'))
 probe=json.loads(subprocess.check_output([a.ffprobe,'-v','error','-show_format','-of','json',str(path)]));dur=float(probe['format']['duration'])/3+2.1
 raw=subprocess.check_output([a.ffmpeg,'-v','error','-ss','3','-i',str(path),'-vf',TONE+',scale=1920:1080','-frames:v','1','-f','image2pipe','-c:v','png','-'])
 photo=Image.open(io.BytesIO(raw)).convert('RGBA');shade=Image.new('RGBA',(W,H),(13,24,38,160));opening=Image.alpha_composite(photo,shade);d=ImageDraw.Draw(opening)
 text(d,(100,300),name,140,700,'#ffffff');text(d,(108,495),'Real-world navigation',48,500,'#e6eef5');text(d,(108,608),'Office · TV · 3× speed',34,500,'#e6eef5')
 opening.convert('RGB').save(a.output/(slug+'-intro.png'))
 photo.convert('RGB').save(a.output/(slug+'-poster.jpg'),quality=95)
 overlay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(overlay)
 d.rounded_rectangle((34,30,400,116),22,fill=(242,247,250,225),outline=(255,255,255,230),width=2)
 text(d,(57,44),name,44,650)
 d.rounded_rectangle((1720,30,1886,110),22,fill=(242,247,250,225),outline=(255,255,255,230),width=2);text(d,(1745,48),'3×',38,600)
 d.rounded_rectangle((34,907,1886,1047),24,fill=(243,247,250,232),outline=(255,255,255,230),width=2)
 text(d,(62,925),'Walk straight to the glass wall, then turn right\nand stop in front of the large TV set.',38,500)
 overlay.save(a.output/(slug+'-overlay.png'))
 silent=a.output/(slug+'-silent.mp4')
 fc=f'[0:v]format=yuv420p,setsar=1[op];[1:v]setpts=(PTS-STARTPTS)/3,fps=30,{TONE},scale=1920:1080,format=yuv420p,setsar=1[cam];[cam][2:v]overlay=0:0:shortest=1[scene];[op][scene]xfade=transition=fade:duration=0.4:offset=2.1,format=yuv420p[v]'
 run(['-loop','1','-framerate','30','-t','2.5','-i',str(a.output/(slug+'-intro.png')),'-i',str(path),'-loop','1','-framerate','30','-i',str(a.output/(slug+'-overlay.png')),'-filter_complex_threads','2','-filter_complex',fc,'-map','[v]','-t',str(dur),'-an','-c:v','libx264','-preset','fast','-crf','19','-maxrate','7M','-bufsize','14M','-threads','4','-pix_fmt','yuv420p','-r','30','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-map_metadata','-1','-movflags','+faststart',str(silent)],slug+'-render.log')
 af=f'atrim=0:{dur},asetpts=PTS-STARTPTS,afade=t=in:d=1.5,afade=t=out:st={dur-3}:d=3'
 analysis=subprocess.run([a.ffmpeg,'-hide_banner','-i',str(a.music),'-af',af+',loudnorm=I=-25:TP=-3:LRA=20:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
 measured=json.loads(re.findall(r'\{\s*"input_i".*?\}',analysis.stderr,re.S)[-1]);gain=-25-float(measured['input_i'])
 final=a.output/(slug+'.mp4');run(['-i',str(silent),'-i',str(a.music),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',af+f',volume={gain}dB','-c:a','aac','-b:a','192k','-ar','48000','-t',str(dur),'-map_metadata','-1','-movflags','+faststart',str(final)],slug+'-mix.log')
 manifest.append({'id':slug,'method':name,'source':str(path.relative_to(a.source_root)),'source_duration_seconds':float(probe['format']['duration']),'duration_seconds':dur,'speed':3,'dimensions':[W,H],'fps':30,'phone_tonemap':TONE,'music':'Lonely Dance — Vexento','music_gain_db':gain,'target_loudness_lufs':-25,'file':final.name,'poster':slug+'-poster.jpg'})
 (a.output/'method-gallery.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Rendered',name,flush=True)
