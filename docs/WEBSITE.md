# Website and release video

GitHub Pages serves this static `docs/` directory through the repository workflow. Preview it with `python -m http.server 8765 --directory docs`. There is no framework build or external font dependency.

## Video

The project page loads one YouTube embed only after the visitor presses Play. The README links a still thumbnail to the same video, since GitHub Markdown does not render YouTube iframes. The released film contains an opening title and three original real-world routes: office TV, hallway red carpet, and campus chair. Motion is encoded at 3×; the viewer should leave YouTube playback at 1×.

The upload master is 3840×2160 at 29.97 fps after the iMovie export. Its panoramic inputs are native 1280×640 at 10 fps; its external cameras are 1920×1080 HLG recordings. The 4K frame is the composition size, not a claim of native 4K camera detail. Phone footage is tone-mapped from BT.2020 HLG into BT.709 SDR with Hable highlight roll-off. No masking, brightness boost, or intermediate compressed demo is used. The two cameras use fixed start offsets; the phone's final frame is held where its recorder stops earlier. Capture metadata and original camera audio are removed. The final iMovie edit adds 0.6-second cross dissolves and an instrumental soundtrack, with a 2.5-second fade-in and 6-second fade-out. Navigation footage remains at 3×; source edges overlap during transitions.

The original recordings, source-rendering scripts, editable iMovie library, and master are kept on T9 outside this Git repository. The iMovie library is stored inside the APFS sparse disk image on T9. `tools/build_release_film.py` prepares the source-derived scene clips; the final transitions and soundtrack are assembled in iMovie. The site tracks thumbnails and `assets/media/film.json`, not MP4/GIF files. Older media remain in Git history; no history rewrite is needed for this release.

To replace the video, update the `data-video-id` and watch URL in `index.html`, the watch URL in `../README.md`, and the ID in `assets/media/film.json`. Replace `film-poster.jpg` and the social card if the footage changes. Keep the embed's descriptive title and click-to-load behavior.

### Soundtrack attribution

“Machinery of the Stars” by Scott Buckley, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Track and license](https://www.scottbuckley.com.au/library/machinery-of-the-stars/). The score is excerpted, leveled, and faded for the film. Keep the attribution in the YouTube description whenever uploading or replacing this edit.

## Paper content

`tools/build_project_content.py` regenerates the three marked main-result table slots from manuscript-derived content using `tools/project-page-curation.json`. The success-rate slot is derived from `realworld_navigation` in `assets/research-data.json`. Preserve the marked slots when editing HTML. The downloadable paper retains all experiments and ablations.

## Design and licenses

See [DESIGN.md](DESIGN.md) for the JanusVLN layout reference, liquid-glass treatment, and accessibility fallbacks. The site uses self-hosted Geist; the film uses Geist and Gilda Display. Both licenses are included. Platform and Phosphor icon provenance is in [assets/icons/README.md](assets/icons/README.md).

Before deployment, check desktop and mobile layouts, keyboard controls, the YouTube link and embed, table overflow, citation copying, local links, and the disabled arXiv control.
