#!/usr/bin/env python3
"""Build silent, 3x research visualizations from original recordings on T9.

Preserves every source frame and the native aspect ratio. Ended comparison
recordings hold their final frame with a visible label; no outcomes are inferred.
"""
import argparse, json, math, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--font', type=Path, required=True)
p.add_argument('--ffmpeg', default='/opt/homebrew/bin/ffmpeg')
p.add_argument('--ffprobe', default='/opt/homebrew/bin/ffprobe')
p.add_argument('--only-simulation', action='store_true')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
W, H = 2560, 1440

def font(size, weight=500):
    f = ImageFont.truetype(str(a.font), size)
    f.set_variation_by_axes([weight]); return f

def write(d, xy, s, size=40, color='#f5f5f7', weight=500):
    d.text(xy, s, font=font(size, weight), fill=color, spacing=15)

def probe(path):
    return json.loads(subprocess.check_output([a.ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))

def run(args, name):
    with (a.output / (name + '.log')).open('w') as log:
        subprocess.run([a.ffmpeg, '-y', '-hide_banner', *args], stdout=log, stderr=log, check=True)

ENC = ['-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-threads', '6', '-r', '30', '-map_metadata', '-1', '-movflags', '+faststart']
manifest = {'speed': 3, 'audio': 'silent research visualizations', 'comparison': [], 'simulation': []}
ours = a.source_root / 'realworld/supplement/PanoVLN_office_tv_1/navigation.mp4'
instruction = 'Walk straight to the glass wall, then turn right and stop in front of the large TV set.'
offset = 0
for n, (method, folder) in enumerate([('NaVid','NaVid_office_tv_1'), ('NaVILA','NaVILA_office_tv_2'), ('StreamVLN','StreamVLN_office_tv_1'), ('JanusVLN','JanusVLN_office_tv_1')]):
    if a.only_simulation: break
    path = a.source_root / 'realworld/supplement' / folder / 'navigation.mp4'
    times = [float(probe(x)['format']['duration']) / 3 for x in [ours, path]]
    duration = math.ceil(max(times)*30)/30 + 1
    panel = Image.new('RGB', (W,H), '#000000'); d = ImageDraw.Draw(panel)
    write(d, (74,48), 'Real-world comparison', 64, weight=650)
    write(d, (2270,67), '3× speed', 36, '#a1a1a8')
    write(d, (74,167), 'PanoVLN', 48, '#a8d1ff', 600)
    write(d, (1322,167), method, 48, weight=600)
    d.rounded_rectangle((64,250,1238,1150), 24, fill='#141416')
    d.rounded_rectangle((1322,250,2496,1150), 24, fill='#141416')
    write(d, (74,1220), '\n'.join(textwrap.wrap(instruction, 105)), 40)
    write(d, (74,1368), 'Shared office instruction · Native fields of view · Complete recordings', 28, '#a1a1a8')
    bg = a.output / f'compare-{n}-bg.png'; panel.save(bg)
    fc = '[0:v]setsar=1[bg];'
    for i,t in enumerate(times):
        fc += f'[{i+1}:v]setpts=(PTS-STARTPTS)/3,fps=30,scale=1174:900:force_original_aspect_ratio=decrease:flags=lanczos,pad=1174:900:(ow-iw)/2:(oh-ih)/2:color=0x141416,setsar=1,tpad=stop_mode=clone:stop_duration={duration}[p{i}];'
    fc += '[bg][p0]overlay=64:250[x];[x][p1]overlay=1322:250[y];'
    for i,t in enumerate(times):
        fpath = str(a.font).replace(':', '\\:')
        fc += f"[{'y' if i==0 else 'z'}]drawtext=fontfile='{fpath}':text='Recording ended':fontsize=30:fontcolor=white:box=1:boxcolor=black@0.85:boxborderw=14:x={94 if i==0 else 1352}:y=1090:enable='gte(t,{t})'[{'z' if i==0 else 'v'}];"
    out = a.output / f'comparison-{n}.mp4'
    run(['-loop','1','-framerate','30','-i',str(bg),'-i',str(ours),'-i',str(path),'-filter_complex_threads','2','-filter_complex',fc.rstrip(';'),'-map','[v]','-t',str(duration),*ENC,str(out)],f'comparison-{n}')
    manifest['comparison'].append({'method':method,'source':str(path.relative_to(a.source_root)),'ours_source':str(ours.relative_to(a.source_root)),'start':offset,'duration':duration,'source_duration':times[1]*3,'ours_duration':times[0]*3})
    offset += duration
    print('Rendered comparison',method,flush=True)
lst = a.output/'comparison-concat.txt'
lst.write_text('\n'.join(f"file '{a.output / f'comparison-{i}.mp4'}'" for i in range(4)))
if not a.only_simulation:
    run(['-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(a.output/'PanoVLN_method_comparison_3x.mp4')],'comparison-final')
else:
    manifest['comparison'] = json.loads((a.output/'visualizations.json').read_text())['comparison']
for slug, folder, title in [('simulation-01','r2r/episode_72','Living room to porch'),('simulation-02','rxr/episode_8632','Hallway to sliding door')]:
    source = a.source_root / folder / 'navigation.mp4'; meta=probe(source)
    instruction = (source.parent/'instruction.txt').read_text().strip()
    panel = Image.new('RGB',(W,H),'#000000'); d=ImageDraw.Draw(panel)
    write(d,(76,62),'PanoVLN',64,weight=650);write(d,(76,161),title,52,weight=600)
    write(d,(2270,84),'3× speed',36,'#a1a1a8')
    write(d,(76,1340),'VLN-CE · Panoramic observation and top-down trajectory',34,'#a1a1a8')
    # Instructions stay above the complete panorama/map, without covering either.
    lines=textwrap.wrap(instruction,114)
    write(d,(76,263),'\n'.join(lines),36)
    bg=a.output/(slug+'-bg.png');panel.save(bg)
    dur=float(meta['format']['duration'])/3
    fc='[1:v]setpts=(PTS-STARTPTS)/3,fps=30,scale=2400:-2:flags=lanczos,setsar=1[p];[0:v][p]overlay=80:600:shortest=1,format=yuv420p[v]'
    run(['-loop','1','-framerate','30','-i',str(bg),'-i',str(source),'-filter_complex_threads','2','-filter_complex',fc,'-map','[v]','-t',str(dur),*ENC,str(a.output/(slug+'.mp4'))],slug)
    manifest['simulation'].append({'id':slug,'title':title,'source':str(source.relative_to(a.source_root)),'instruction':instruction,'source_duration':dur*3,'duration':dur,'source_fps':meta['streams'][0]['r_frame_rate'],'source_dimensions':[meta['streams'][0]['width'],meta['streams'][0]['height']]})
    print('Rendered',slug,flush=True)
for filename in ['PanoVLN_method_comparison_3x','simulation-01','simulation-02']:
    run(['-ss','1','-i',str(a.output/(filename+'.mp4')),'-frames:v','1','-vf','scale=1600:-1',str(a.output/(filename+'-poster.jpg'))],filename+'-poster')
(a.output/'visualizations.json').write_text(json.dumps(manifest,indent=2)+'\n')
