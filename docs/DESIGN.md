# Project-page design

PanoVLN’s page leads with original navigation footage, followed by demonstrations, a shared-instruction comparison, the method, main benchmark results, downloadable resources, and citation. Deep teal (`#086b63`), pale surfaces, Manrope headings, and DM Sans body text provide a consistent visual system. The header combines original robot and simulation footage with a typographic project name. Phosphor supplies interface icons; platform marks use their official sources. Asset provenance and licenses are recorded in [assets/icons/README.md](assets/icons/README.md).

## References and access

- [JanusVLN](https://github.com/MIV-XJTU/JanusVLN): a readable progression from installation and data preparation to training, evaluation, and deployment informs the repository documentation.
- [InternNav](https://github.com/InternRobotics/InternNav): the motion-led repository introduction inspired a footage-based header. PanoVLN uses its own asymmetrical four-view composition, footage, colors, and typography.

- [Design Prompts — Swiss Minimalist](https://www.designprompts.dev/swiss-minimalist): the public **Prompt** button opened its readable prompt without an account. The useful ideas are asymmetric grids, clear alignment, strong heading hierarchy, numbered sections, and responsive stacking. The page adapts these principles without copying its full prompt, red palette, or heavy borders.
- [VibUI — planetary pulse](https://vibui.dev/prompts/planetary-pulse): its prompt is publicly readable and the entry appears in the [free catalog](https://vibui.dev/free), although the detail page also says “Members only.” Its large looping-media composition informed the video-first hierarchy. No source-code unlock or external media was used.
- [Aura — Robotics Spatial Control](https://www.aura.build/s/industrial-robotics-73): a public rendered template, used only as a visual comparison for large typography and grouped technical information. Its original generation prompt was not available in the inspected preview.
- [Jiro](https://jiro.build/): the Finsyc **Copy Prompt** action required login. Its original prompt was not obtained. Only the publicly visible pale-sky atmosphere was considered as visual inspiration.

## PanoVLN adaptation prompt

This brief was written for this project; it is not a copied external prompt:

> Build a calm academic project page around a large original navigation video. Use a pale opening section and deep teal accents. Keep the project title, authors, affiliations, and working code/model/data links easy to scan. Give the same-instruction robot comparison a distinct section with synchronized playback, native video proportions, and complete recordings. Explain the method briefly, then present readable main-result tables and charts backed by the paper. Finish with setup resources and citation. Use mature, sourced icons and actual research figures. On mobile, stack content naturally, preserve media proportions, keep controls reachable, and respect reduced-motion preferences. Every claim must correspond to released assets or reported results.

Browser playback and selectors are implemented in the website. The accompanying Figma file records visual design states; the deployed site is the reference for interactive behavior.
