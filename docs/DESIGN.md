# PanoVLN research page

## Direction

JanusVLN informs the centered research hierarchy and wide media. Apple product pages inform the black canvas, large type and restrained, floating controls. The page contains the paper's teaser, exact abstract, real-world film, model architecture, dataset pipeline, main results, method comparison, VLN-CE visualizations, resources and citation. Ablations remain in the paper.

## Tokens and layout

- Black `#000000`: canvas.
- Charcoal `#141416`: media and citation surface.
- White `#f5f5f7`: primary text.
- Gray `#a1a1a8`: secondary text.
- Blue `#8bc4ff`: links and selected results.
- Graphite `#303034`: table separators.

Self-hosted Geist throughout; 66–104px project name, 25–38px paper title, 34–56px section titles, 18–20px body and 15–17px controls. Research content is 1120px wide; videos are 1280px wide. Authors form four columns on desktop and two on mobile. Paper figures retain their white canvas and original colors.

Glass is reserved for navigation, resource controls, play buttons and the comparison chapter selector. The effect uses a translucent material, backdrop blur and saturation, bright upper rim, dark lower edge and pointer-responsive reflection. Content itself stays crisp. Reduced transparency replaces glass with a solid surface; reduced motion disables transitions and smooth scrolling. This is a CSS approximation of the material, not Apple's native renderer.

## Adapted design prompt

> Build a dark academic project page for panoramic vision-and-language navigation. Use a true black background, large neutral sans-serif type, centered title and authors, and full-width, unrotated media. Keep the research hierarchy explicit: teaser, abstract, method, dataset pipeline, main results and videos. Reserve liquid glass for floating controls: diffused backdrop, a fine reflective rim, subtle inner shadow and interaction-driven highlights. Keep charts and body text on clear, stable surfaces. Preserve every image's original aspect ratio. Show execution efficiency directly. Do not add slogans, decorative illustrations or an ablation gallery.

This prompt is an original synthesis of the references below, not a copied template. All footage and research assets belong to this project; no Apple or JanusVLN visual assets are reused.

## References

- [JanusVLN project page](https://miv-xjtu.github.io/JanusVLN.github.io/)
- [Apple iPhone](https://www.apple.com/sg/iphone-18-pro/), [iPad Pro](https://www.apple.com/sg/ipad-pro/), [MacBook Pro](https://www.apple.com/sg/macbook-pro/)
- [Apple: Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/) — material, hierarchy and interaction
- [Design for AI: Liquid Glass](https://designforai.dev/style/liquid-glass) — prompt and CSS treatment
- [Liquid Glass design prompts](https://liquidglassdesign.com/prompts) — prompt references

## Verification

Check 390px, 768px and 1440px layouts, keyboard focus, table scrolling, citation copying and reduced-motion behavior. Only a clicked video loads an external player; switching videos removes the previous player. Inspect full video frames and endpoint labels, and verify duration, color metadata and audio loudness before upload. Masters stay on T9.
