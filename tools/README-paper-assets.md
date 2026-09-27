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

`build_project_content.py` updates the static benchmark tables and complete figure gallery in `docs/index.html`, and writes browser-safe provenance to `docs/assets/research-data.json`. PNG exports are optional working assets and are ignored by Git; the published page uses WebP and the original PDFs.
