# PanoVLN: illuminated research gallery

## Direction and references

The [JanusVLN project page](https://miv-xjtu.github.io/JanusVLN.github.io/) informs the centered research hierarchy and independent two-column video galleries. [Apple MacBook Pro](https://www.apple.com/sg/macbook-pro/) and [iPad Pro](https://www.apple.com/sg/ipad-pro/) inform the relationship between a dark stage, localized colored light, strong white typography, and restrained controls. Assets and layout are independently implemented for PanoVLN.

## Visual plan

- Midnight blue `#0c1225`: page background, visibly chromatic instead of pure black.
- Cobalt `#426dcc` and iris `#7661ba`: soft, broad illumination around the title and media galleries.
- Ice `#f1f4fc`: primary text.
- Mist `#bac6dc`: secondary text.
- White `#ffffff`: original paper figures and tables, preserving their printed colors.

Geist remains the sole type family. The centered project title is the primary visual event; full-title reflected light and a broad blue-violet halo sit behind it. Section headings and controls remain quiet. Body text has a narrower reading measure. Videos stay level, full-field, two per row on desktop and one per row on phones. Glass is limited to navigation and resource controls. There are no decorative slogans or repeating explanatory subtitles.

```
       glass navigation
    title / authors / links        ← localized blue-violet light
           teaser
      abstract / main film
 architecture / data / results     ← original white paper plates
     6 real-world recordings       ← broad muted gallery light
       4 baseline methods
       6 simulation routes
     models / data / citation
```

Review against the brief: the previous uniform pale background and the earlier pure-black treatment are both replaced by a chromatic illuminated canvas. Color remains behind content, never as a filter on experimental footage. The paper figures stay white for legibility. The galleries gain different scenes and routes, not repeated cuts from the same film; these are qualitative examples, not new aggregate experimental claims.

## Adapted design prompt

> Design an academic panoramic-navigation page as a deep midnight-blue gallery illuminated by broad cobalt and iris light. Use the restrained product staging of Apple Pro pages and the clear academic order of JanusVLN, without copying their graphics or wording. Center the title and authors, keep compact two-column video galleries, retain original white LaTeX figure plates, and use reflective glass only for navigation and controls. Show actual project material, readable type, and no empty marketing subtitles. Respect reduced motion and transparency; videos load only when requested.

## Liquid material revision

Scope: navigation, resource pills, citation control, and media play buttons only. Retain the halo palette, typography, research hierarchy, figures, and all seventeen films.

Apple's [Liquid Glass introduction](https://www.apple.com.cn/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/) describes refraction, reflection, and highlights that respond to interaction. Its [Materials guidance](https://developer.apple.com/design/human-interface-guidelines/materials) recommends the highly translucent clear variant above rich media. The implementation approach is informed by [Kube's CSS/SVG optics exploration](https://kube.io/blog/liquid-glass-css-svg/); the code and rounded-lens displacement field are written for this site.

The previous 24px backdrop blur and opaque gray play-button tint flattened the material. Replace them with a mostly clear center, a narrow displaced optical rim, opposing edge highlights, and a pointer-driven reflection. Use only a small readability diffusion on the navigation. Media buttons refract their own poster using a standard SVG image filter, which does not require SVG backdrop-filter support; the poster disappears when playback starts. Chromium can additionally refract the actual page backdrop beneath the pills and navigation. Other browsers receive the clear reflective CSS surface for those controls. These are web approximations, not Apple's native compositor.

Keep the material quiet over text: displace only the background, never labels or icons. Build maps on size changes rather than in an animation loop. Honor reduced transparency with solid surfaces and reduced motion with stationary highlights.
