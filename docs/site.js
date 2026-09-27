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
const viewButtons = [...document.querySelectorAll('[data-view]')];
const demoSpeed = $('#demo-speed');
const chapterSelect = $('#demo-chapter');
let scenes = [];
let selectedKind = 'realworld';
let selectedScene = null;
let selectedView = 'panorama';
let activeChapter = 0;
let pendingSeek = 0;
let playWhenReady = false;
const mediaRoot = 'assets/media/';
const originalsRoot = `${mediaRoot}originals/`;
function clockTime(seconds) {
  const value = Math.max(0, Math.round(seconds));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
}
function originalURL(file) { return /^https:\/\//.test(file) ? file : `${originalsRoot}${file}`; }
function panoramaTime() {
  if (!selectedScene?.original || selectedView === 'panorama') return demo.currentTime;
  const sync = selectedScene.original.external.synchronization_reference;
  const seconds = selectedScene.original.external.chapters[activeChapter].source_start_seconds + demo.currentTime;
  return sync.panorama_seconds + (seconds - sync.external_seconds) / sync.external_seconds_per_panorama_second;
}
function loadDemoFile(file, poster, width, height, seek = 0, play = false) {
  demo.pause();
  pendingSeek = seek;
  playWhenReady = play;
  demo.poster = poster;
  demo.preload = 'metadata';
  demo.src = file;
  demo.style.aspectRatio = `${width} / ${height}`;
  $('#demo-open').href = file;
  demo.load();
}
demo.addEventListener('loadedmetadata', () => {
  demo.playbackRate = Number(demoSpeed.value);
  demo.currentTime = Math.min(Math.max(0, pendingSeek), Math.max(0, demo.duration - .05));
  if (playWhenReady) demo.play().catch(() => {});
  playWhenReady = false;
});
demo.addEventListener('play', () => pauseOtherMedia('demo'));
demo.addEventListener('error', () => { $('#demo-note').textContent = 'This recording could not load. Try the Open video link or select another view.'; });
demoSpeed.addEventListener('change', () => { demo.defaultPlaybackRate = Number(demoSpeed.value); demo.playbackRate = Number(demoSpeed.value); });
function loadChapter(index, seek = 0, play = false) {
  activeChapter = index;
  const chapter = selectedScene.original.external.chapters[index];
  chapterSelect.value = String(index);
  loadDemoFile(originalURL(chapter.file), originalURL(chapter.poster), 1920, 1080, seek, play);
  $('#demo-note').textContent = `Full 1080p camera recording · ${clockTime(chapter.source_start_seconds)}–${clockTime(chapter.source_end_seconds)} of ${clockTime(selectedScene.original.external.master.duration_seconds)}. ${selectedScene.original.external.chapters.length > 1 ? 'Chapters play continuously.' : 'Original timing and audio.'}`;
}
chapterSelect.addEventListener('change', () => loadChapter(Number(chapterSelect.value), 0, !demo.paused));
demo.addEventListener('ended', () => {
  if (selectedView === 'external' && selectedScene?.original && activeChapter + 1 < selectedScene.original.external.chapters.length) loadChapter(activeChapter + 1, 0, true);
});
function loadView(view, time = 0, play = false, startAtBeginning = false) {
  selectedView = view;
  for (const button of viewButtons) button.setAttribute('aria-pressed', String(button.dataset.view === view));
  const original = selectedScene.original;
  const external = view === 'external';
  const timing = caption.querySelector('.scene-name small');
  if (timing) timing.textContent = `${clockTime(external ? original.external.master.duration_seconds : original.panorama.duration_seconds)} · ${external ? 'Camera recording' : 'Full route'}`;
  $('#demo-chapter-label').hidden = !external || original.external.chapters.length < 2;
  demo.setAttribute('aria-label', `${selectedScene.title}: ${external ? 'full third-person camera recording' : 'full first-person panorama recording'}`);
  if (external) {
    const sync = original.external.synchronization_reference;
    const target = startAtBeginning ? 0 : Math.max(0, Math.min(original.external.master.duration_seconds - .05, sync.external_seconds + (time - sync.panorama_seconds) * sync.external_seconds_per_panorama_second));
    const chapters = original.external.chapters;
    const index = Math.max(0, chapters.findIndex(c => target >= c.source_start_seconds && target < c.source_end_seconds));
    loadChapter(index, target - chapters[index].source_start_seconds, play);
  } else {
    const clip = original.panorama;
    loadDemoFile(originalURL(clip.file), originalURL(clip.poster), clip.width, clip.height, time, play);
    $('#demo-note').textContent = 'Full first-person panorama · 1280 × 640 · 10 fps. Original video frames and timing, with no re-encoding.';
  }
}
for (const button of viewButtons) button.addEventListener('click', () => {
  if (selectedView === button.dataset.view || !selectedScene?.original) return;
  const position = panoramaTime();
  const playing = !demo.paused;
  loadView(button.dataset.view, position, playing);
});
function chooseScene(scene, play = false) {
  selectedScene = scene;
  const realworld = !!scene.original;
  $('#demo-view-controls').hidden = !realworld;
  $('#demo-chapter-label').hidden = true;
  caption.replaceChildren();
  const title = document.createElement('span'); title.className = 'scene-name'; title.textContent = scene.title;
  const timing = document.createElement('small'); timing.textContent = `${clockTime(scene.duration)} · ${realworld ? 'Full route' : 'Simulation'}`; title.append(timing);
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
  if (realworld) {
    chapterSelect.replaceChildren();
    scene.original.external.chapters.forEach((chapter, index) => {
      const option = document.createElement('option'); option.value = String(index); option.textContent = `${clockTime(chapter.source_start_seconds)}–${clockTime(chapter.source_end_seconds)}`; chapterSelect.append(option);
    });
    loadView(selectedView, 0, play, true);
  } else {
    loadDemoFile(`${mediaRoot}${scene.id}.mp4`, `${mediaRoot}${scene.id}.jpg`, scene.width, scene.height, 0, play);
    demo.setAttribute('aria-label', `${scene.title}: full simulation recording`);
    $('#demo-note').textContent = 'Full simulation routes. Original timing and 3 fps sampling are preserved; the route map remains visible.';
  }
}
function selectEnvironment(kind, focus = false) {
  selectedKind = kind;
  for (const tab of tabs) { const selected = tab.dataset.kind === kind; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; if (selected && focus) tab.focus(); }
  $('#demo-panel').setAttribute('aria-labelledby', `tab-${kind}`);
  sceneList.className = `scene-list ${kind}`; sceneList.replaceChildren();
  const group = scenes.filter(scene => scene.type === kind);
  for (const scene of group) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'scene'; button.dataset.id = scene.id; button.setAttribute('aria-pressed', 'false');
    const img = document.createElement('img'); img.src = scene.original ? originalURL(scene.original.panorama.poster) : `${mediaRoot}${scene.id}.jpg`; img.alt = ''; img.loading = 'lazy';
    const labels = document.createElement('span'); const name = document.createElement('strong'); name.textContent = scene.title;
    const duration = document.createElement('small'); duration.textContent = `${clockTime(scene.duration)} · Full route`;
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
Promise.all([
  fetch('assets/media/scenes.json').then(r => { if (!r.ok) throw new Error('Missing scenes'); return r.json(); }),
  fetch('assets/media/originals/manifest.json').then(r => { if (!r.ok) throw new Error('Missing original recordings'); return r.json(); })
]).then(([base, originals]) => {
  scenes = [
    ...originals.scenes.map(scene => ({ id: `realworld-${scene.id}`, type: 'realworld', title: scene.name, instruction: scene.instruction, duration: scene.panorama.duration_seconds, original: scene })),
    ...base.filter(scene => scene.type === 'simulation')
  ];
  selectEnvironment(selectedKind);
}).catch(() => { $('#demo-note').textContent = 'Scene selection could not load. The full office panorama is still available above.'; tabs.forEach(t => t.disabled = true); viewButtons.forEach(t => t.disabled = true); });

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
  const finished = comparisonVideos.every(v => v.ended);
  const started = comparisonVideos.some(v => v.currentTime > 0);
  comparisonButton.querySelector('span').textContent = playing ? 'Pause both' : finished ? 'Replay together' : started ? 'Resume both' : 'Play together';
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
  const replay = comparisonVideos.every(v => v.ended);
  if (replay) resetComparison();
  pauseOtherMedia('comparison');
  // Keep an ended recording on its final frame while the other one resumes.
  const pending = replay ? comparisonVideos : comparisonVideos.filter(v => !v.ended);
  const results = await Promise.allSettled(pending.map(v => v.play()));
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
