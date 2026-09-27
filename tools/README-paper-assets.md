# Rebuild paper figures and result tables

These scripts export the PanoVLN multi-file LaTeX project supplied with the paper. They do not change the source manuscript or its experimental values. Run the commands from the repository root, passing the directory that contains `main.tex`, `Sections/`, and `Figures/`.

```bash
python -m pip install -r tools/requirements-paper.txt
python tools/export_paper_figures.py --paper-root /path/to/latex-project
python tools/extract_paper_content.py --paper-root /path/to/latex-project
python tools/build_project_content.py build/paper-content/paper-content.json
```

`export_paper_figures.py` writes 3200-pixel WebP/PNG previews and the original vector PDFs into `docs/assets/figures/`. It trims only exterior white margins and retains a small border. The asset manifest is `build/paper-content/figure-assets.json`. Use WebP on the page and link the original PDF for full-resolution viewing. Options: `--output-dir`, `--manifest`, and `--max-pixels`.

`extract_paper_content.py` writes `build/paper-content/paper-content.json` and individual semantic HTML table fragments. Every result row points back to its LaTeX file and line or to the source PDF. Options: `--asset-manifest` and `--output-dir`.

The seven LaTeX result tables are parsed from `Sections/4.exp.tex` and `Sections/6.appendix.tex`. The real-world SR/NE chart values were individually transcribed and visually verified. A SHA-256 guard stops export if that figure changes, so old values cannot silently follow a new chart. Author order and the release summary match the supplied manuscript and should be reviewed when preparing a later release.

All 15 supplied figure PDFs are included. The two files that are not currently referenced by the manuscript have `used_in_current_paper: false`. The JSON also records two source inconsistencies, preserving the original assets and taking benchmark values from the actual LaTeX tables.

For the public PDF, compile the paper's `public_preprint.tex` entry point using Tectonic or an existing TeX installation, and copy its resulting PDF to `docs/assets/paper/PanoVLN.pdf`. This entry point displays the authors with a `Preprint` page header. The original `main.tex` retains its existing review-mode setting.

## Curated project-page results

`build_project_content.py` renders three main-result tables: the selected simulation benchmark, real-world success rate, and real-world execution efficiency. Each shows five methods. `project-page-curation.json` selects source tables, methods and columns by name; all values come from the extracted JSON. Keep the marked `benchmark-table`, `realworld-table`, and `efficiency-table` slots in the HTML. Missing or duplicate slots stop the builder before it writes the page.

All eight source tables, 15 figure records, and source notes remain in `docs/assets/research-data.json`. The public page shows the architecture and main results, with efficiency in a disclosure; the full paper contains the ablations. `render_realworld_sr.py` remains available as an optional standalone chart exporter, but the website uses HTML tables for readable labels on small screens.

## Release film

`build_release_film.py` renders the three selected real-world routes from their original recordings, with an opening title and 3× playback. Keep the working files and upload master outside Git, preferably on the volume containing the originals. The FFmpeg build must include `zscale`, `tonemap`, `h264_metadata`, and `libx264`.

```bash
python tools/build_release_film.py \
  --source-root /path/to/navigation_demo \
  --output /path/to/release-film \
  --font-dir /path/to/fonts \
  --ffmpeg /path/to/ffmpeg
```

The font directory contains `Geist.ttf` (the variable font) and `GildaDisplay.ttf`, obtained from the official [Google Fonts repository](https://github.com/google/fonts), under their SIL Open Font Licenses. The script requires Pillow. Its manifest records the source files, fixed camera offsets, speed, resolution, and HDR-to-SDR filter. The film is muted, has no masks, and removes capture metadata. Upload `PanoVLN_navigation_release.mp4` to YouTube; see `docs/WEBSITE.md` for linking it. Do not add the MP4 or rendering intermediates to this repository.
