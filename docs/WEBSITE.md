# Project website

The project page is a static HTML/CSS/JavaScript site in `docs/`. It has no build-time JavaScript dependencies. Fonts, images, panoramic recordings, comparison recordings, and the paper PDF are served by Pages. Complete 1080p camera recordings are hosted as GitHub Release assets.

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
- Simulation scenes and instructions: `docs/assets/media/scenes.json`.
- Original real-world recordings, timing, and camera URLs: `docs/assets/media/originals/manifest.json`.
- Animated project header: `docs/assets/media/project-banner.json` and `tools/build_project_banner.py`.
- Five-method office comparison: `docs/assets/media/comparison/manifest.json`.
- Visual direction, reference prompts, and icon selection: [`DESIGN.md`](DESIGN.md).
- Paper-derived figures and tables: follow [`tools/README-paper-assets.md`](../tools/README-paper-assets.md).
- Replace the disabled arXiv button with a link after the identifier is available, then update the README badge and citation metadata together.

The header uses original navigation footage and the PanoVLN name; it has no project pictogram or promotional tagline. The favicon uses the sourced Phosphor Panorama Duotone icon. Interface and platform icons, provenance, and licenses are in [`assets/icons/`](assets/icons/README.md). `assets/brand/social-card.png` is the 1200 × 630 sharing image; its editable source is `tools/social-card.html`. Render it after fonts and images load.


## Main-result content

The results section contains two semantic HTML tables: selected simulation baselines and real-world execution efficiency, each with five methods. The selection in [`tools/project-page-curation.json`](../tools/project-page-curation.json) names rows and columns without duplicating numeric values. Run `tools/build_project_content.py` against the extracted paper-content JSON to refresh the two marked slots in `index.html`. The complete source tables and figure records remain in `assets/research-data.json` for provenance; the page does not render a full figure gallery or ablations.

The architecture illustration is followed by three independent real-world success-rate panels for Hallway, Office and Campus. [`tools/render_realworld_sr.py`](../tools/render_realworld_sr.py) creates these SVGs with Matplotlib from the same source JSON, retaining all five methods, exact values and the same 0–100% scale. Their source and values are recorded in `assets/figures/realworld-sr-provenance.json`. See the [asset rebuilding guide](../tools/README-paper-assets.md) for commands and font dependencies.

## Media delivery

The README opens with an eight-second animated mosaic made from two original robot camera recordings and two simulation panoramas. The corresponding 1920 × 872 H.264 video appears on the project page. These are overview assets; the gallery provides complete recordings in separate full-width players.

The real-world gallery switches between the original first-person panorama and the external camera:

- **First person:** all original H.264 video frames are copied without re-encoding. Office, hallway, and campus recordings retain 1280 × 640, 10 fps, complete durations, and original timestamps.
- **External camera:** complete 1920 × 1080 recordings retain the original approximately 60 fps timing and audio. The original HLG/HEVC recordings are tone mapped to SDR and encoded once as H.264 at CRF 16 for browser support. They are not cropped, resized, retimed, or masked. Large MP4s are served from the [`navigation-media-v4` release](https://github.com/wangzhen-w/PanoVLN/releases/tag/navigation-media-v4), keeping them out of the Git history and Pages artifact.
- **Playback:** starts at 1× with 2×/4× controls. Switching camera views uses a documented approximate timing correspondence. Native video controls allow seeking, fullscreen playback, and unmuting the camera audio. MP4s have their metadata at the front for streaming. Preload is limited to metadata for the selected clip; other videos load only when selected.

`assets/media/originals/manifest.json` records source-relative paths, sizes, checksums, dimensions, frame rates, timing mappings, and verification results. `assets/media/project-banner.json` records the overview composition separately. No earlier low-resolution or anonymized supplementary export is used as a source.

The five-method comparison uses the complete original first-person recordings from one shared office-to-TV task: PanoVLN, JanusVLN, StreamVLN, NaVILA and NaVid. Streams are copied without re-encoding, cropping, resizing or masking. Files retain 1× timestamps and 10 fps; the comparison starts at a shared 1× playback speed and offers 2×/4×. Each recording runs to its own endpoint. Selecting a baseline resets both players. Pause / Resume preserve position; Restart returns to the beginning. A finished recording stays on its final frame while the other continues. Once both have ended, Replay together starts again. Success/failure labels are not inferred from the qualitative videos.

Simulation recordings preserve source timing and 3 fps sampling. The hero plays muted only while visible and when reduced motion is not requested. Starting another recording pauses unrelated videos. All recordings are illustrative examples; the tables report quantitative evaluation.

Font licenses for Manrope and DM Sans are included in `assets/fonts/`. The banner's Instrument Sans typography uses the [SIL Open Font License](https://github.com/Instrument/instrument-sans/blob/main/OFL.txt). Model, dataset, and code terms remain in the repository's License section.
