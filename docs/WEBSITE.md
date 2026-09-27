# Website and release videos

GitHub Pages serves this static `docs/` directory through the repository workflow. Preview it with `python -m http.server 8765 --directory docs`. There is no framework build or external font dependency.

## Publishing this revision

The main film currently points to the published `_QsBD9Mlrw4` upload. The three new player IDs (`COMPARE_VIDEO`, `SIM_ONE`, `SIM_TWO`) must be replaced after their YouTube uploads are processed. They are not publishable IDs. The Pages workflow runs `tools/check_project_page.py` to reject pending IDs or missing local assets; use `--allow-pending-videos` only for local checks. The locally remixed main film also needs a new upload. Do not deploy this draft before resolving them.

For the main film, update the ID and watch URL in `index.html`, the two watch URLs in `../README.md`, and the metadata in `assets/media/film.json`. For the research videos, update their `data-video-id` values in `index.html`. Retain comparison chapter starts at 0, 33, 57 and 98 seconds. Verify each upload's HD playback and embedding before publishing.

## Real-world film

The released film contains an opening title and three original routes: office TV, hallway red carpet and campus chair. Navigation is encoded at 3×; viewers should leave YouTube playback at 1×. The README links a still thumbnail to YouTube because GitHub Markdown does not render YouTube iframes.

The main master is 3840×2160 at 29.97 fps. Panorama inputs are native 1280×640 at 10 fps; external cameras are 1920×1080 HLG recordings. The 4K frame is the composition size, not native 4K camera detail. Phone footage is tone-mapped from BT.2020 HLG to BT.709 SDR with Hable highlight roll-off. Each route preserves the full 16:9 external-camera frame and complete 2:1 panorama inset. Fixed start offsets align the cameras; the final phone frame holds if that recorder stops first. There are no masks, extra exposure boosts or crops. Original camera audio and capture metadata are removed. iMovie supplies 0.6-second cross dissolves between scenes.

The revised local master, `PanoVLN_widescreen_4K_Lonely_Dance.mp4`, copies this video stream without re-encoding. Its replacement soundtrack is excerpted to the 112.25-second film, faded in over 2.5 seconds and out over 6 seconds, and mixed to approximately −25 LUFS, about 8 dB below the previous release. The existing online film and its `film.json` metadata remain unchanged until the replacement upload is ready.

### Music credit

The revised film uses **Lonely Dance — Vexento**, selected from [the supplied NetEase track](https://music.163.com/#/song?id=1301409077). The artist's [official upload description](https://www.youtube.com/watch?v=tvQvpIy9JnA) permits use in videos and requests a channel or SoundCloud link. Include this credit in the new YouTube description:

> Music: “Lonely Dance” by Vexento. https://www.youtube.com/watch?v=tvQvpIy9JnA — excerpted, leveled and faded.

This is artist permission, not a Creative Commons license. The previous `_QsBD9Mlrw4` upload uses “Machinery of the Stars” by Scott Buckley under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); preserve [its attribution](https://www.scottbuckley.com.au/library/machinery-of-the-stars/) on that unchanged upload.

## Method comparison and VLN-CE

`tools/build_visualization_films.py` creates three silent research films directly from original recordings. All navigation uses a common 3× time scale. It requires Pillow, a variable Geist TTF, FFmpeg with `drawtext` and `libx264`, and FFprobe. Pass the paths explicitly:

```bash
python tools/build_visualization_films.py \
  --source-root /path/to/navigation_demo \
  --output /path/to/rendered-films \
  --font /path/to/Geist.ttf \
  --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

`PanoVLN_method_comparison_3x.mp4` presents PanoVLN beside NaVid, NaVILA, StreamVLN and JanusVLN sequentially. Each uses the same office-TV instruction. Full native fields of view are preserved. When a shorter recording ends, its final frame holds with an explicit “Recording ended” label; this does not label the trial as successful or failed. The full film lasts 148.7 seconds.

`simulation-01.mp4` uses `r2r/episode_72`; `simulation-02.mp4` uses `rxr/episode_8632`. They preserve the original panorama-plus-map composites and complete instructions. Both sources were recorded at 3 fps. At 3× they contain nine distinct source frames per second, repeated into the 30 fps output; no interpolated observations or trajectories are invented. The research films use a 2560×1440 H.264 CRF 16 canvas. Their source provenance is in `assets/media/visualizations.json`.

Each player loads a privacy-enhanced YouTube embed after a click. Opening another player removes the previous player to prevent simultaneous playback. The comparison buttons jump to the four method chapters. No MP4 or GIF files are added to Git.

## Source files and paper content

Original recordings, rendered masters and editable iMovie work remain on T9 outside Git. The iMovie library lives inside an APFS sparse disk image on T9. `tools/build_release_film.py` prepares the main film's scenes. The site tracks posters and metadata only.

`tools/build_project_content.py` regenerates the three marked table slots using `tools/project-page-curation.json`. The simulation table includes all 24 rows and 13 columns of the main table; the real-world success and execution-efficiency tables are also shown directly. The abstract is copied from the manuscript. Only teaser, model architecture and dataset pipeline figures are displayed. Keep original numeric values and generated table-slot markers when editing HTML.

See [DESIGN.md](DESIGN.md) for design references and accessibility fallbacks. Font and [icon licenses](assets/icons/README.md) are included. Before publishing, verify mobile layouts, all four YouTube players, chapter seeking, table overflow, citation copying, local links and the disabled arXiv control.
