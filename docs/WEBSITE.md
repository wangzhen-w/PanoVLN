# Project website

The project page is a static HTML/CSS/JavaScript site in `docs/`. It has no build-time JavaScript dependencies. Fonts, images, videos, and the paper PDF are served locally.

## Preview

From the repository root:

```bash
python3 -m http.server 8765 --directory docs
```

Open `http://localhost:8765`. Use an HTTP server: scene metadata is loaded with `fetch`, so opening `index.html` directly as a local file is not supported.

## Publish on GitHub Pages

In repository Settings → Pages, select **GitHub Actions** as the source. The `Deploy project page` workflow publishes `docs/` when a change to the site reaches `main`, or when manually dispatched. The expected URL is `https://wangzhen-w.github.io/PanoVLN/`.

## Update content

- Page layout and links: `docs/index.html`.
- Colors, typography, responsive layout: `docs/styles.css`.
- Video controls, scene tabs, citation copy: `docs/site.js`.
- Scenes and instructions: `docs/assets/media/scenes.json`.
- Five-method office comparison: `docs/assets/media/comparison/manifest.json`.
- Visual direction, reference prompts, and icon selection: [`DESIGN.md`](DESIGN.md).
- Paper-derived figures and tables: follow [`tools/README-paper-assets.md`](../tools/README-paper-assets.md).
- Replace the disabled arXiv button with a link after the identifier is available, then update the README badge and citation metadata together.

`assets/brand/logo.svg` and `wordmark.svg` use the official Phosphor Panorama Duotone icon. The source geometry is preserved; the primary fill is teal. Interface and platform icons, provenance and licenses are in [`assets/icons/`](assets/icons/README.md). `assets/brand/social-card.png` is the 1200 × 630 sharing image. Its editable HTML source is `tools/social-card.html`; render it at 1200 × 630 after fonts and images load. GitHub's repository social preview can use the same image.

## Main-result content

The results section contains two semantic HTML tables: selected simulation baselines and real-world execution efficiency, each with five methods. The selection in [`tools/project-page-curation.json`](../tools/project-page-curation.json) names rows and columns without duplicating numeric values. Run `tools/build_project_content.py` against the extracted paper-content JSON to refresh the two marked slots in `index.html`. The complete source tables and figure records remain in `assets/research-data.json` for provenance; the page does not render a full figure gallery or ablations.

The architecture illustration is followed by three independent real-world success-rate panels for Hallway, Office and Campus. [`tools/render_realworld_sr.py`](../tools/render_realworld_sr.py) creates these SVGs with Matplotlib from the same source JSON, retaining all five methods, exact values and the same 0–100% scale. Their source and values are recorded in `assets/figures/realworld-sr-provenance.json`. See the [asset rebuilding guide](../tools/README-paper-assets.md) for commands and font dependencies.

## Media delivery

The page uses a 33-second silent 1080p H.264 highlight reel, four simulation routes, and three real-world routes. Real-world videos are rebuilt directly from the original navigation and phone recordings. The 2560 × 720 gallery retains the full native 1280 × 640 first-person panorama in each dual-view video, without downscaling or anonymization masks. Each web derivative uses one final H.264 encode at CRF 16; phone HDR is tone mapped to SDR for browser compatibility. MP4 files use `faststart`. Videos are loaded on demand; the hero plays muted only when visible and when reduced motion is not requested. Scene and comparison players retain native playback controls; the hero exposes them after a user starts playback.

The five-method comparison uses the complete original first-person recordings from one shared office-to-TV task: PanoVLN, JanusVLN, StreamVLN, NaVILA and NaVid. Video streams are copied without re-encoding, cropping, resizing or masking. Files retain 1× timestamps and 10 fps; the browser starts at a common 2× playback speed and offers 1×/4×. Each recording runs to its own endpoint. Selecting a baseline pauses/resets both players, and Play together starts both from the beginning. Native controls permit individual inspection. Success/failure labels are not inferred from the qualitative videos.

Simulation source recordings are 3 fps; their sampling cadence is preserved. Real-world recordings play at 2×, and the campus example is explicitly labeled as an excerpt. Videos are illustrative examples, not a substitute for the benchmark evaluation. The README uses a lightweight animated preview linked to the full demo page.

Font licenses for Manrope and DM Sans are included in `assets/fonts/`. Model, dataset, and code terms remain described in the repository's License section.
