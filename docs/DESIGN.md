# PanoVLN research page — liquid glass

The current layout follows the research hierarchy of the [JanusVLN project page](https://miv-xjtu.github.io/JanusVLN.github.io/): a split paper identity / research visual, followed by Abstract, Demo Video, Approach, Experiments, and BibTeX. PanoVLN adds practical model and data links. The page uses its own copy, footage, figures, typography, and implementation.

## Visual system

| Token | Value |
| --- | --- |
| Ice background | `#EEF3FA` |
| Primary text | `#15243B` |
| Secondary text | `#4D6178` |
| Ocean accent | `#1558A6` |
| White | `#FFFFFF` |
| Mist | `#D6E8F3` |
| Typeface | Geist, self-hosted |
| Main width | 1160 px |
| Body text | 19 px desktop / 17 px mobile |

Liquid glass is concentrated in the floating navigation, resource buttons, photographic frames, and player control. Translucent surfaces combine backdrop blur, bright inner rims, a shaded lower edge, and soft shadows. A faint background derived from the panoramic observation gives the glass something to transmit. Pointer highlights respond only to deliberate interaction; there is no continuous floating animation.

The title, author information, and links form a compact left column. Two unobscured views from the TV navigation route form the right visual: the Unitree Go2 and its panoramic observation. Main sections share one content column with centered headings. Figures and table cells remain sharp, with no filter applied to their contents. The page has no invented slogan, decorative stats strip, ablation gallery, or custom illustrated logo.

The mobile layout stacks the research header and keeps table overflow inside each table. Focus states, semantic table headers, clipboard fallback, reduced-motion behavior, reduced-transparency preferences, and an opaque backdrop-filter fallback are included.

## Assets and earlier references

Photographs are taken from PanoVLN's original recordings. The external camera still uses the same HLG-to-SDR conversion as the release film; the panorama comes directly from the native recording. Research values come from `assets/research-data.json`, with provenance to the manuscript. Icons use Phosphor and official platform sources; see [icon provenance](assets/icons/README.md).

The preceding cream/serif proposal used the accessible Jiro Blogs Luxterra and Footer 04 Kelo prompts. This revision replaces that visual direction in response to the author's requested JanusVLN layout and liquid-glass treatment. Those templates are no longer the website's design specification. The film retains its existing title treatment; its font licenses remain included alongside the site font license.
