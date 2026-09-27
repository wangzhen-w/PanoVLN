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
- Paper-derived figures and tables: follow [`tools/README-paper-assets.md`](../tools/README-paper-assets.md).
- Replace the disabled arXiv button with a link after the identifier is available, then update the README badge and citation metadata together.

`assets/brand/logo.svg` and `wordmark.svg` are editable vector assets. `assets/brand/social-card.png` is the 1200 × 630 sharing image. Its editable HTML source is `tools/social-card.html`; render it at 1200 × 630 after fonts and images load. GitHub's repository social preview can use the same image.

## Media delivery

The page uses a 33-second silent 1080p H.264 highlight reel, four simulation routes, and three real-world routes. Real-world videos are rebuilt directly from the original navigation and phone recordings. The 2560 × 720 gallery retains the full native 1280 × 640 first-person panorama in each dual-view video, without downscaling or anonymization masks. Each web derivative uses one final H.264 encode at CRF 16; phone HDR is tone mapped to SDR for browser compatibility. MP4 files use `faststart`. Videos are loaded on demand; the hero plays muted only when visible and when reduced motion is not requested. All players retain native playback controls.

Simulation source recordings are 3 fps; their sampling cadence is preserved. Real-world recordings play at 2×, and the campus example is explicitly labeled as an excerpt. Videos are illustrative examples, not a substitute for the benchmark evaluation. The README uses a lightweight animated preview linked to the full demo page.

Font licenses for Manrope and DM Sans are included in `assets/fonts/`. Model, dataset, and code terms remain described in the repository's License section.
