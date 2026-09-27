#!/usr/bin/env python3
"""Build the project header from original navigation recordings (Pillow + FFmpeg)."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
p.add_argument('--ffmpeg', required=True, help='FFmpeg build with zscale and libx264')
p.add_argument('--font', type=Path, required=True, help='Instrument Sans Bold or compatible font')
p.add_argument('--output', type=Path, default=Path('docs/assets/media'))
a = p.parse_args()
a.work_dir.mkdir(parents=True, exist_ok=True)
a.output.mkdir(parents=True, exist_ok=True)
canvas = Image.new('RGB', (1920, 872), '#eff4f1')
d = ImageDraw.Draw(canvas)
d.rectangle((632, 548, 1288, 872), fill='#eff4f1')
d.text((960, 643), 'PanoVLN', font=ImageFont.truetype(str(a.font), 108), anchor='mm', fill='#163f39')
for y, line in [(729, 'Towards Effective Panoramic'), (766, 'Vision-and-Language Navigation')]:
    d.text((960, y), line, font=ImageFont.truetype(str(a.font), 27), anchor='mm', fill='#4a6058')
canvas.save(a.work_dir / 'canvas.png')
clips = [
    ('realworld/PanoVLN_office_water_dispenser_1/video_20260920_132240.mp4', 12, True, 0, 0, 954, 536),
    ('realworld/PanoVLN_campus_chair_1/video_20260920_164421.mp4', 24, True, 966, 0, 954, 536),
    ('r2r/episode_896/navigation.mp4', 3, False, 0, 548, 632, 324),
    ('r2r/episode_72/navigation.mp4', 7, False, 1288, 548, 632, 324),
]
tone = 'zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:param=0.3:desat=0,zscale=t=bt709:m=bt709:r=tv'
args = ['-loop', '1', '-i', str(a.work_dir / 'canvas.png')]
filters = []
for i, (path, start, hdr, x, y, w, h) in enumerate(clips, 1):
    args += ['-ss', str(start), '-t', '8', '-i', str(a.source_root / path)]
    process = tone + ',' if hdr else 'crop=1280:640:0:0,'
    # Preserve each source's aspect ratio; the simulation views have a narrow border.
    filters.append(f'[{i}:v]setpts=PTS-STARTPTS,fps=30,{process}scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0xeff4f1,setsar=1,format=yuv420p[v{i}]')
prev = '0:v'
for i, (_, _, _, x, y, _, _) in enumerate(clips, 1):
    filters.append(f'[{prev}][v{i}]overlay={x}:{y}:shortest=1[b{i}]')
    prev = f'b{i}'
video = a.output / 'project-banner.mp4'
def run(args):
    subprocess.run([a.ffmpeg, '-nostdin', '-y', '-v', 'warning', *map(str, args)], check=True)
run(args + ['-filter_complex_threads', '2', '-filter_complex', ';'.join(filters), '-map', f'[{prev}]', '-t', '8', '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-threads', '3', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-map_metadata', '-1', '-movflags', '+faststart', video])
run(['-ss', '1', '-i', video, '-frames:v', '1', '-q:v', '1', a.output / 'project-banner.jpg'])
run(['-i', video, '-vf', 'fps=10,scale=1280:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle', '-loop', '0', a.output / 'project-banner.gif'])
(a.output / 'project-banner.json').write_text(json.dumps({
    'purpose': 'Animated repository header, separate from full-resolution demonstration recordings.',
    'duration_seconds': 8, 'width': 1920, 'height': 872, 'font': 'Instrument Sans Bold (SIL Open Font License)',
    'clips': [{'source_relative_path': c[0], 'start_seconds': c[1], 'duration_seconds': 8, 'source_speed': 1, 'HDR_to_SDR': c[2]} for c in clips],
    'outputs': {'mp4': {'fps': 30, 'codec': 'H.264', 'crf': 14}, 'gif': {'width': 1280, 'fps': 10, 'palette_colors': 256}},
    'redaction': False,
}, indent=2) + '\n')
