'use strict';
const $ = selector => document.querySelector(selector);
const hero = $('#hero-video');
const demo = $('#demo-video');
const heroToggle = $('#hero-toggle');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let heroPausedByUser = false;
let activeMedia = 'hero';
function pauseOtherMedia(except) {
  activeMedia = except;
  for (const video of document.querySelectorAll('video')) {
    const group = video.id.startsWith('compare-') ? 'comparison' : video === hero ? 'hero' : 'demo';
    if (group !== except) video.pause();
  }
}
function updateHero() {
  const playing = !hero.paused;
  $('#hero-cover-play').hidden = playing;
  heroToggle.querySelector('span').textContent = playing ? 'Pause film' : 'Play film';
  heroToggle.querySelector('img').src = `assets/icons/phosphor/regular/${playing ? 'pause' : 'play'}.svg`;
  heroToggle.setAttribute('aria-label', playing ? 'Pause overview film' : 'Play overview film');
}
hero.addEventListener('play', () => { pauseOtherMedia('hero'); updateHero(); });
hero.addEventListener('pause', updateHero);
heroToggle.addEventListener('click', () => {
  heroPausedByUser = !hero.paused;
  if (hero.paused) { hero.controls = true; hero.play().catch(() => {}); } else hero.pause();
});
$('#hero-cover-play').addEventListener('click', () => { heroPausedByUser = false; hero.controls = true; hero.play().catch(() => {}); });
new IntersectionObserver(entries => {
  const visible = entries[0].isIntersecting;
  if (!visible) hero.pause();
  else if (!heroPausedByUser && activeMedia === 'hero' && !reduceMotion.matches && !navigator.connection?.saveData) hero.play().catch(() => {});
}, {threshold: .5}).observe(hero);
reduceMotion.addEventListener('change', () => { if (reduceMotion.matches) hero.pause(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) document.querySelectorAll('video').forEach(v => v.pause()); });

const sceneList = $('#scene-list');
const caption = $('.demo-caption');
const tabs = [...document.querySelectorAll('[data-kind]')];
let scenes = [];
let selectedKind = 'realworld';
demo.addEventListener('play', () => pauseOtherMedia('demo'));
function chooseScene(scene, play = false) {
  demo.pause();
  demo.poster = `assets/media/${scene.id}.jpg`;
  demo.src = `assets/media/${scene.id}.mp4`;
  demo.style.aspectRatio = `${scene.width} / ${scene.height}`;
  demo.setAttribute('aria-label', `${scene.title}: ${scene.scope}`);
  caption.replaceChildren();
  const title = document.createElement('span'); title.className = 'scene-name'; title.textContent = scene.title;
  const timing = document.createElement('small'); timing.textContent = scene.type === 'realworld' ? '2× playback' : 'Simulation'; title.append(timing);
  const instruction = document.createElement('p'); instruction.textContent = scene.instruction;
  caption.append(title, instruction);
  if (scene.instruction.length > 330) {
    const full = scene.instruction;
    const text = document.createElement('span'); text.textContent = full.slice(0, 270) + '…';
    const expand = document.createElement('button'); expand.className = 'instruction-toggle'; expand.textContent = 'Read full instruction'; expand.setAttribute('aria-expanded', 'false');
    expand.addEventListener('click', () => { const wasExpanded = expand.getAttribute('aria-expanded') === 'true'; text.textContent = wasExpanded ? full.slice(0,270) + '…' : full; expand.setAttribute('aria-expanded', String(!wasExpanded)); expand.textContent = wasExpanded ? 'Read full instruction' : 'Show less'; });
    instruction.replaceChildren(text, expand);
  }
  for (const button of sceneList.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.id === scene.id));
  $('#demo-note').textContent = scene.type === 'realworld' ? `Robot panorama and external camera · 2× playback. ${scene.id === 'realworld-campus' ? '24-second route excerpt.' : 'Full edited route.'}` : 'Full simulation routes. Original timing and 3 fps sampling are preserved; the route map remains visible.';
  if (play) demo.play().catch(() => {});
}
function selectEnvironment(kind, focus = false) {
  selectedKind = kind;
  for (const tab of tabs) { const selected = tab.dataset.kind === kind; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; if (selected && focus) tab.focus(); }
  $('#demo-panel').setAttribute('aria-labelledby', `tab-${kind}`);
  sceneList.className = `scene-list ${kind}`; sceneList.replaceChildren();
  const group = scenes.filter(scene => scene.type === kind);
  for (const scene of group) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'scene'; button.dataset.id = scene.id; button.setAttribute('aria-pressed', 'false');
    const img = document.createElement('img'); img.src = `assets/media/${scene.id}.jpg`; img.alt = ''; img.loading = 'lazy';
    const labels = document.createElement('span'); const name = document.createElement('strong'); name.textContent = scene.title;
    const duration = document.createElement('small'); duration.textContent = `${Math.round(scene.duration)} sec ${scene.id === 'realworld-campus' ? 'excerpt' : 'route'}`;
    labels.append(name, duration); button.append(img, labels); button.addEventListener('click', () => chooseScene(scene, true)); sceneList.append(button);
  }
  if (group.length) chooseScene(group[0]);
}
for (const tab of tabs) {
  tab.addEventListener('click', () => selectEnvironment(tab.dataset.kind));
  tab.addEventListener('keydown', e => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (tabs.indexOf(tab) + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    selectEnvironment(tabs[next].dataset.kind, true);
  });
}
fetch('assets/media/scenes.json').then(r => { if (!r.ok) throw new Error('Missing scenes'); return r.json(); }).then(data => { scenes = data; selectEnvironment(selectedKind); }).catch(() => { $('#demo-note').textContent = 'Scene selection could not load. The office recording is still available above.'; tabs.forEach(t => t.disabled = true); });

const ours = $('#compare-ours');
const baseline = $('#compare-baseline');
const comparisonVideos = [ours, baseline];
const comparisonButton = $('#compare-play');
const baselineSelect = $('#baseline-select');
const speed = $('#compare-speed');
let clips = [];
function currentSpeed() { return Number(speed.value); }
function updateComparisonButton() {
  const playing = comparisonVideos.some(v => !v.paused && !v.ended);
  comparisonButton.querySelector('span').textContent = playing ? 'Pause both' : 'Play together';
  comparisonButton.querySelector('img').src = `assets/icons/phosphor/regular/${playing ? 'pause' : 'play'}.svg`;
}
function updateStatus(video) {
  const status = video === ours ? $('#ours-status') : $('#baseline-status');
  const clip = clips.find(c => c.id === video.dataset.clip);
  if (!clip) return;
  status.textContent = `${clip.duration_seconds.toFixed(1)} s recording · ${video.ended ? 'Recording ended' : video.paused ? 'Paused' : `Playing at ${video.playbackRate}×`}`;
}
function resetComparison() {
  for (const video of comparisonVideos) { video.pause(); if (video.readyState > 0) video.currentTime = 0; updateStatus(video); }
  updateComparisonButton();
}
function setComparisonClip(video, clip) {
  if (!clip) throw new Error('Missing comparison clip');
  video.pause(); video.dataset.clip = clip.id;
  video.src = `assets/media/comparison/${clip.video}`;
  video.poster = `assets/media/comparison/${clip.poster}`;
  video.setAttribute('aria-label', `${clip.method}: complete office-to-TV navigation recording`);
  video.defaultPlaybackRate = currentSpeed(); video.playbackRate = currentSpeed();
  updateStatus(video);
}
for (const video of comparisonVideos) {
  video.addEventListener('play', () => { pauseOtherMedia('comparison'); updateStatus(video); updateComparisonButton(); });
  for (const event of ['pause', 'ended', 'ratechange']) video.addEventListener(event, () => { updateStatus(video); updateComparisonButton(); });
  video.addEventListener('loadedmetadata', () => { video.playbackRate = currentSpeed(); });
  video.addEventListener('error', () => { $('#comparison-error').textContent = 'A recording could not load. Please reload the page or open the videos from the repository.'; });
}
comparisonButton.disabled = true;
baselineSelect.disabled = true;
speed.disabled = true;
baselineSelect.addEventListener('change', () => { resetComparison(); setComparisonClip(baseline, clips.find(c => c.id === baselineSelect.value)); });
$('#compare-restart').addEventListener('click', resetComparison);
speed.addEventListener('change', () => { comparisonVideos.forEach(v => { v.defaultPlaybackRate = currentSpeed(); v.playbackRate = currentSpeed(); }); });
comparisonButton.addEventListener('click', async () => {
  if (comparisonVideos.some(v => !v.paused && !v.ended)) { comparisonVideos.forEach(v => v.pause()); return; }
  // A new joint playback starts from the same point even after independent inspection.
  resetComparison(); pauseOtherMedia('comparison');
  const results = await Promise.allSettled(comparisonVideos.map(v => v.play()));
  if (results.some(r => r.status === 'rejected')) $('#comparison-error').textContent = 'Use the play controls inside each video to start playback.';
  else $('#comparison-error').textContent = '';
});
fetch('assets/media/comparison/manifest.json').then(r => { if (!r.ok) throw new Error('Missing comparison'); return r.json(); }).then(data => {
  clips = data.clips; setComparisonClip(ours, clips.find(c => c.id === 'panovln')); setComparisonClip(baseline, clips.find(c => c.id === baselineSelect.value));
  $('#ours-time').textContent = '360° panoramic view'; comparisonButton.disabled = false; baselineSelect.disabled = false; speed.disabled = false;
}).catch(() => { $('#comparison-error').textContent = 'Comparison metadata could not load. Reload the page to try again.'; baselineSelect.disabled = true; });

$('#copy-citation').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('#citation').textContent); $('#copy-citation').textContent = 'Copied'; $('#copy-status').textContent = 'Citation copied to clipboard.'; setTimeout(() => { $('#copy-citation').textContent = 'Copy BibTeX'; $('#copy-status').textContent = ''; }, 2400); }
  catch { const range = document.createRange(); range.selectNodeContents($('#citation')); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); $('#copy-status').textContent = 'Citation selected. Press Control+C or Command+C to copy.'; }
});
