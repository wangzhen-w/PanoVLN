'use strict';
const hero = document.querySelector('#hero-video');
const heroToggle = document.querySelector('#hero-toggle');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let userPaused = false;
function updateHeroButton() { heroToggle.textContent = hero.paused ? 'Play film' : 'Pause'; heroToggle.setAttribute('aria-label', hero.paused ? 'Play highlight video' : 'Pause highlight video'); }
hero.addEventListener('play', updateHeroButton);
hero.addEventListener('pause', updateHeroButton);
heroToggle.addEventListener('click', async () => { if (hero.paused) { userPaused = false; await hero.play().catch(() => {}); } else { userPaused = true; hero.pause(); } });
const heroObserver = new IntersectionObserver(entries => { for (const entry of entries) { if (!entry.isIntersecting) hero.pause(); else if (!reduceMotion.matches && !userPaused) hero.play().catch(() => {}); } }, {threshold: .15});
heroObserver.observe(hero);
reduceMotion.addEventListener('change', () => { if (reduceMotion.matches) hero.pause(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) { hero.pause(); document.querySelector('#demo-video').pause(); } });

const demo = document.querySelector('#demo-video');
const list = document.querySelector('#scene-list');
const caption = document.querySelector('.demo-caption');
const tabs = [...document.querySelectorAll('[role=tab]')];
let scenes = [];
function chooseScene(scene, shouldPlay = false) {
  demo.pause();
  demo.poster = `assets/media/${scene.id}.jpg`;
  demo.src = `assets/media/${scene.id}.mp4`;
  demo.setAttribute('aria-label', `${scene.title}: ${scene.scope}`);
  demo.style.aspectRatio = `${scene.width} / ${scene.height}`;
  caption.replaceChildren();
  const title = document.createElement('span'); title.className = 'scene-name'; title.textContent = `${scene.title} · ${scene.type === 'realworld' ? '2× playback' : 'Simulation'}`; caption.append(title);
  const instruction = document.createElement('span'); instruction.textContent = scene.instruction; caption.append(instruction);
  if (scene.instruction.length > 330) {
    instruction.textContent = scene.instruction.slice(0, 260) + '…';
    const expand = document.createElement('button'); expand.className = 'instruction-toggle'; expand.textContent = 'Read full instruction'; expand.setAttribute('aria-expanded', 'false');
    expand.addEventListener('click', () => { const expanded = expand.getAttribute('aria-expanded') === 'true'; instruction.textContent = expanded ? scene.instruction.slice(0, 260) + '…' : scene.instruction; expand.setAttribute('aria-expanded', String(!expanded)); expand.textContent = expanded ? 'Read full instruction' : 'Show less'; }); caption.append(expand);
  }
  for (const b of list.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.id === scene.id));
  document.querySelector('#demo-note').textContent = scene.type === 'realworld' ? `Robot panorama and external camera · 2× playback. ${scene.id === 'realworld-campus' ? 'This 24-second excerpt shows part of the route.' : 'Full edited route.'}` : 'Full source routes. Simulation recordings are sampled at 3 fps; playback retains the original timing. The map is preserved beside the panorama.';
  if (shouldPlay) demo.play().catch(() => {});
}
function selectEnvironment(kind, focus = false) {
  for (const t of tabs) { const selected = t.dataset.kind === kind; t.setAttribute('aria-selected', String(selected)); t.tabIndex = selected ? 0 : -1; if (selected && focus) t.focus(); }
  document.querySelector('#demo-panel').setAttribute('aria-labelledby', `tab-${kind}`);
  list.className = `scene-list ${kind}`; list.replaceChildren();
  const group = scenes.filter(s => s.type === kind);
  for (const scene of group) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'scene'; b.dataset.id = scene.id; b.setAttribute('aria-pressed', 'false');
    const img = document.createElement('img'); img.src = `assets/media/${scene.id}.jpg`; img.alt = ''; img.loading = 'lazy';
    const labels = document.createElement('span'); const title = document.createElement('strong'); title.textContent = scene.title; const duration = document.createElement('small'); duration.textContent = `${Math.round(scene.duration)} sec${scene.id === 'realworld-campus' ? ' excerpt' : ' route'}`; labels.append(title, duration); b.append(img, labels); b.addEventListener('click', () => chooseScene(scene, true)); list.append(b);
  }
  if (group.length) chooseScene(group[0]);
}
for (const tab of tabs) {
  tab.addEventListener('click', () => selectEnvironment(tab.dataset.kind));
  tab.addEventListener('keydown', e => { if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) { e.preventDefault(); const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (tabs.indexOf(tab) + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length; selectEnvironment(tabs[next].dataset.kind, true); } });
}
fetch('assets/media/scenes.json').then(r => { if (!r.ok) throw new Error('Missing scenes'); return r.json(); }).then(data => { scenes = data; selectEnvironment('realworld'); }).catch(() => { caption.textContent = 'Open the navigation video above, or explore demonstrations in the repository.'; for(const tab of tabs) tab.disabled = true; });

const copy = document.querySelector('#copy-citation');
copy.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(document.querySelector('#citation').textContent); copy.textContent = 'Copied'; document.querySelector('#copy-status').textContent = 'Citation copied to clipboard.'; setTimeout(() => {copy.textContent = 'Copy'; document.querySelector('#copy-status').textContent = '';}, 2400); }
  catch { const range = document.createRange(); range.selectNodeContents(document.querySelector('#citation')); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); document.querySelector('#copy-status').textContent = 'Citation selected. Press Ctrl+C or Command+C to copy.'; }
});
