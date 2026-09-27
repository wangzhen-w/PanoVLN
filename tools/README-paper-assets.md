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

`build_project_content.py` renders only the two main-result tables in `docs/index.html`: the selected simulation benchmark and real-world execution efficiency. Each table shows five methods. [`project-page-curation.json`](project-page-curation.json) selects source tables, methods and columns by name; all displayed values come from the extracted JSON. The page must contain the `benchmark-table` and `efficiency-table` slots with their matching end comments. The builder refuses to overwrite a page with missing or duplicate slots. Use `--site` for another template directory or `--curation` for another selection file.

The builder also preserves all eight source tables, 15 figure records and source notes in `docs/assets/research-data.json` for provenance. It does not generate a complete figure gallery or ablation tables. The landing page uses the architecture figure and three compact real-world success-rate panels.

Rebuild those panels after updating the source JSON:

```bash
uv run --with matplotlib --with fonttools --with brotli tools/render_realworld_sr.py
```

Alternatively, install those three Python packages in your existing environment and run `python tools/render_realworld_sr.py`. The default input is `docs/assets/research-data.json`; pass a content JSON file as a positional argument to use another export. Options: `--output-dir`, `--font-dir`, and `--preview-dir` for optional PNG review images.

`render_realworld_sr.py` uses Matplotlib to write `realworld-sr-hallway.svg`, `realworld-sr-office.svg`, and `realworld-sr-campus.svg`. All five methods remain visible on a common 0–100% axis, with direct method and value labels. PanoVLN is dark teal and the other methods are muted gray-blue. The script uses the local DM Sans or Manrope font when readable and otherwise DejaVu Sans. The original SR values come from the verified `realworld_navigation` table; no extra averaging or uncertainty is introduced. Each SVG includes a title and description, and `realworld-sr-provenance.json` records the source, exact values and rendering metadata.

PNG exports are optional working assets and are ignored by Git. The page uses WebP for the architecture and SVG for the three SR panels; original figure PDFs remain available for full-resolution inspection.
