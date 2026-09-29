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

The public paper is hosted on [arXiv](https://arxiv.org/abs/2609.34759); use its [PDF](https://arxiv.org/pdf/2609.34759) for reading. Do not copy a full-paper PDF into the repository. Keep local compilations outside Git when regenerating figure or table crops.

## Curated project-page results

The current project page uses original figure assets and image crops of the typeset simulation and execution-efficiency tables, each linked to a vector PDF crop. Execution efficiency is always visible. `docs/assets/tables/sources.json` records the exact source snapshot, its SHA-256, page numbers, and crop rectangles. The historical snapshot is recorded for reproducibility; the reader-facing paper link points to arXiv.

The extraction scripts and `build_project_content.py` are legacy provenance tools for the former HTML-table layout. The latter requires its marked table slots and does not update the current image-based page. To refresh the current tables, render new crops from the updated manuscript, inspect every row and column, and update `sources.json`. See `docs/WEBSITE.md` for the current page workflow.

## Release film

`build_release_film.py` renders the three selected real-world routes from their original recordings, with an opening title and 3× playback. Keep the working files and upload master outside Git, preferably on the volume containing the originals. The FFmpeg build must include `zscale`, `tonemap`, `h264_metadata`, and `libx264`.

```bash
python tools/build_release_film.py \
  --source-root /path/to/navigation_demo \
  --output /path/to/release-film \
  --font-dir /path/to/fonts \
  --ffmpeg /path/to/ffmpeg
```

The font directory contains `Geist.ttf` (the variable font) and `GildaDisplay.ttf`, obtained from the official [Google Fonts repository](https://github.com/google/fonts), under their SIL Open Font Licenses. The script requires Pillow. Its manifest records the source files, fixed camera offsets, speed, resolution, and HDR-to-SDR filter. The film is muted, has no masks, and removes capture metadata. Publish the final viewing copy as an external video attachment; see `docs/WEBSITE.md` for the current editing, soundtrack, and hosting workflow. Do not add the MP4 or rendering intermediates to this repository.
