# Project page and media

GitHub Pages serves `docs/`. Preview with `python -m http.server 8765 --directory docs`. The site has no framework build and uses self-hosted Geist.

## Native video players

The README embeds the canonical GitHub video attachment URL as a standalone line. GitHub renders its native player; readers stay on the repository. The project page uses the same canonical URL in an HTML `video` element. Do not store a redirect URL containing a temporary signature. Media are hosted as GitHub attachments, not in Git or GitHub Releases.

The main film contains the office TV, hallway red carpet and campus chair routes. Its source-quality 4K master remains on T9. The attachment is a 1920×1080 H.264 viewing copy, encoded with CRF 21 and a 6 Mb/s peak target. The independent method films use PanoVLN, NaVid, NaVILA, StreamVLN and JanusVLN external-camera originals. Each preserves the full 16:9 frame, converts HLG to BT.709 SDR, and adds a 2.5-second opening with a 0.4-second dissolve into the 3× recording. The five methods appear in a two-column grid, each with its own player. No paired comparison or chapter switcher remains.

`tools/build_method_gallery.py` reproduces these method films. It requires Pillow, a variable Geist TTF, FFmpeg with `zscale`, `tonemap` and `libx264`, and the separately supplied music file. `assets/media/method-gallery.json` records original paths, durations, color conversion and mix gain. The two VLN-CE films preserve their original panorama/map composite at 3×, with an opening and music. Simulation sources were recorded at 3 fps; their observations are repeated into a 30 fps output, not interpolated.

All scores use “Lonely Dance” by Vexento, mixed to approximately −25 LUFS with fades. Music permission and credits are in the root [asset guide](../assets/README.md). Original camera sound is removed. Starting a video pauses any other active video. All players use `preload="none"` and posters to avoid downloading eight movies on page load.

## Paper visuals

The teaser, model architecture, dataset construction pipeline and real-world results keep their original figure assets. Simulation and execution-efficiency tables are **image crops from the typeset paper PDF**, not HTML reconstructions. `assets/tables/sources.json` records the PDF hash, page numbers and exact crop rectangles. Each image links to a matching vector PDF crop. The efficiency table is always visible and includes all six metric columns. The full abstract is copied from the manuscript.

The earlier JSON extraction and HTML-table tools remain available for paper provenance, but they do not update the current image-based page. To update tables, render the corresponding regions of a newly compiled paper and update `sources.json`. Inspect both crops for clipped rules, captions and rows.

## Deployment

Make changes directly on `main`. No release or feature branch is required. The Pages workflow checks local assets and rejects unresolved media references before deploying. Verify the eight players, public unauthenticated media access, seek/controls, desktop/mobile grids, citation copying and full-resolution figure links before pushing. See [DESIGN.md](DESIGN.md) for the visual direction.
