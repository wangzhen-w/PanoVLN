#!/usr/bin/env python3
"""Render the three real-world SR panels with Matplotlib, from verified paper data.

Source: paper-content.json / docs/assets/research-data.json,
  table realworld_navigation, transcribed and visually checked against
  Figures/real_world_exp/realworld_exp.pdf (page 1), referenced by
  Sections/4.exp.tex, fig:realworld_navigation.
The source compares 20 shared instruction-route pairs per environment without
scene-specific fine-tuning. No additional aggregation or uncertainty is invented.

Reproduce from the repository root:
  uv run --with matplotlib --with fonttools --with brotli tools/render_realworld_sr.py
Or: python tools/render_realworld_sr.py path/to/paper-content.json
--preview-dir is optional; it writes 480x270 PNGs for visual QA outside the site.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = 'http://www.w3.org/2000/svg'
HIGHLIGHT = '#086b63'
BASELINE = '#b8c9cc'
TEXT = '#243b3d'


def register_font(directory: Path, temporary: Path) -> str:
    """Use the site's actual font when readable, otherwise Matplotlib's fallback."""
    for name in ('dm-sans.woff2', 'manrope.woff2'):
        candidate = directory / name
        if not candidate.is_file():
            continue
        try:
            from fontTools.ttLib import TTFont
            font = TTFont(candidate)
            font.flavor = None
            family = None
            for weight in (400, 700):
                if 'fvar' in font:
                    from fontTools.varLib.instancer import instantiateVariableFont
                    static = instantiateVariableFont(font, {'wght': weight}, inplace=False, updateFontNames=True)
                else:
                    static = font
                converted = temporary / f'{candidate.stem}-{weight}.ttf'
                static.save(converted)
                font_manager.fontManager.addfont(str(converted))
                family = font_manager.FontProperties(fname=str(converted)).get_name()
                if 'fvar' not in font:
                    break
            return family
        except Exception:
            # Optional font decoding/instancing must not block a data export.
            continue
    return 'DejaVu Sans'


def add_accessible_metadata(path: Path, title: str, description: str) -> None:
    """Add SVG accessibility metadata; every plotted graphic is Matplotlib output."""
    ET.register_namespace('', SVG_NS)
    tree = ET.parse(path)
    root = tree.getroot()
    root.set('role', 'img')
    root.set('aria-labelledby', 'chart-title chart-description')
    title_node = ET.Element(f'{{{SVG_NS}}}title', {'id': 'chart-title'})
    title_node.text = title
    description_node = ET.Element(f'{{{SVG_NS}}}desc', {'id': 'chart-description'})
    description_node.text = description
    root.insert(0, title_node)
    root.insert(1, description_node)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', nargs='?', type=Path, default=ROOT / 'docs/assets/research-data.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'docs/assets/figures')
    parser.add_argument('--font-dir', type=Path, default=ROOT / 'docs/assets/fonts')
    parser.add_argument('--preview-dir', type=Path)
    args = parser.parse_args()
    data = json.loads(args.content.read_text())
    source = next(table for table in data['tables'] if table['id'] == 'realworld_navigation')
    methods = [row['cells'][0] for row in source['rows']]
    if len(methods) != 5 or len(set(methods)) != 5 or 'PanoVLN' not in methods:
        raise ValueError('Expected all five methods, including PanoVLN, in the real-world table')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
    manifest = {'source': source['source'], 'source_json_sha256': hashlib.sha256(args.content.read_bytes()).hexdigest(),
                'generator': 'Matplotlib', 'matplotlib_version': matplotlib.__version__,
                'encoding': 'Horizontal bars, common 0–100% axis; five methods retained; no added uncertainty or aggregation.',
                'evaluation': '20 shared instruction-route pairs per setting; no scene-specific fine-tuning.',
                'panels': []}
    with tempfile.TemporaryDirectory(prefix='panovln-chart-font-') as font_tmp:
        family = register_font(args.font_dir, Path(font_tmp))
        manifest['font_family'] = family
        with plt.rc_context({'font.family': family, 'font.size': 11.5, 'svg.fonttype': 'path',
                             'svg.hashsalt': 'panovln-realworld-sr', 'axes.unicode_minus': False}):
            for environment in ('Hallway', 'Office', 'Campus'):
                column = source['columns'].index(f'{environment} SR ↑')
                values = [float(row['cells'][column]) for row in source['rows']]
                if not all(math.isfinite(value) and 0 <= value <= 100 for value in values):
                    raise ValueError(f'Invalid success rate in {environment}')
                # 5 x 2.8125 inches is 480 x 270 CSS pixels at 96 pixels/inch.
                fig, ax = plt.subplots(figsize=(5, 2.8125), dpi=96, facecolor='white')
                fig.subplots_adjust(left=.27, right=.96, bottom=.205, top=.80)
                colors = [HIGHLIGHT if method == 'PanoVLN' else BASELINE for method in methods]
                ax.barh(range(len(methods)), values, height=.53, color=colors, linewidth=0, zorder=3)
                ax.set_yticks(range(len(methods)), methods)
                ax.invert_yaxis()
                ax.set_xlim(0, 100)
                ax.set_xticks([0, 25, 50, 75, 100])
                ax.set_xlabel('Success rate (%)', fontsize=10.5, color=TEXT, labelpad=7)
                ax.tick_params(axis='both', length=0, colors=TEXT)
                ax.tick_params(axis='y', pad=9, labelsize=11.5)
                ax.tick_params(axis='x', pad=6, labelsize=10.5)
                ax.set_axisbelow(True)
                ax.grid(axis='x', color='#e1e8e9', linewidth=.6)
                for spine in ax.spines.values():
                    spine.set_visible(False)
                for label, method in zip(ax.get_yticklabels(), methods):
                    if method == 'PanoVLN':
                        label.set_color(HIGHLIGHT)
                        label.set_weight('bold')
                for y, (method, value) in enumerate(zip(methods, values)):
                    inside = value >= 93
                    ax.text(value - 2.5 if inside else value + 2.2, y, f'{value:g}',
                            ha='right' if inside else 'left', va='center', fontsize=11.5,
                            weight='bold' if method == 'PanoVLN' else 'normal',
                            color='white' if inside else (HIGHLIGHT if method == 'PanoVLN' else TEXT),
                            clip_on=False, zorder=4)
                fig.text(.035, .915, environment, color=TEXT, fontsize=13, fontweight='bold', va='top')
                title = f'{environment}: real-world navigation success rate'
                value_text = '; '.join(f'{method} {value:g}%' for method, value in zip(methods, values))
                description = (f'{value_text}. Common 0–100% axis. 20 shared instruction-route pairs in this setting, '
                               'without scene-specific fine-tuning. Source: Figures/real_world_exp/realworld_exp.pdf, page 1; '
                               'Sections/4.exp.tex, fig:realworld_navigation.')
                path = args.output_dir / f'realworld-sr-{environment.lower()}.svg'
                fig.savefig(path, format='svg', facecolor='white', metadata={'Title': title, 'Description': description,
                                                                          'Creator': f'PanoVLN / Matplotlib {matplotlib.__version__}', 'Date': None})
                add_accessible_metadata(path, title, description)
                if args.preview_dir:
                    fig.savefig(args.preview_dir / path.with_suffix('.png').name, dpi=96, facecolor='white')
                plt.close(fig)
                manifest['panels'].append({'environment': environment, 'file': path.name, 'values': dict(zip(methods, values)),
                                           'css_width': 480, 'css_height': 270, 'alt': description})
                print(f'{path.name}: {dict(zip(methods, values))}')
    (args.output_dir / 'realworld-sr-provenance.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
