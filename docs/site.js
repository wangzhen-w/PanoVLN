'use strict';
const film = document.getElementById('film');
document.getElementById('play-film')?.addEventListener('click', () => {
  const id = film.dataset.videoId;
  if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return;
  const player = document.createElement('iframe');
  player.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`;
  player.title = 'PanoVLN real-world navigation — 3× playback';
  player.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  player.referrerPolicy = 'strict-origin-when-cross-origin';
  player.allowFullscreen = true;
  film.replaceChildren(player);
  player.focus();
});
const copy = document.getElementById('copy-citation');
copy?.addEventListener('click', async () => {
  const status = document.getElementById('copy-status');
  try {
    await navigator.clipboard.writeText(document.getElementById('citation').textContent);
    status.textContent = 'BibTeX copied.';
    copy.textContent = 'Copied';
    setTimeout(() => { copy.textContent = 'Copy BibTeX'; }, 2200);
  } catch {
    const range = document.createRange();
    range.selectNodeContents(document.getElementById('citation'));
    const selection = window.getSelection();
    selection.removeAllRanges(); selection.addRange(range);
    status.textContent = 'Citation selected. Use your browser’s Copy command.';
  }
});

// The highlight responds to the pointer; nothing animates while the page is idle.
if (matchMedia('(hover: hover) and (prefers-reduced-motion: no-preference)').matches) {
  document.querySelectorAll('.glass-control:not(.unavailable)').forEach(control => {
    control.addEventListener('pointermove', event => {
      const rect = control.getBoundingClientRect();
      control.style.setProperty('--pointer-x', `${((event.clientX - rect.left) / rect.width) * 100}%`);
      control.style.setProperty('--pointer-y', `${((event.clientY - rect.top) / rect.height) * 100}%`);
    });
    control.addEventListener('pointerleave', () => {
      control.style.removeProperty('--pointer-x');
      control.style.removeProperty('--pointer-y');
    });
  });
}
