'use strict';
function playFilm(film, start=0) {
  const id=film?.dataset.videoId;
  if(!/^[A-Za-z0-9_-]{11}$/.test(id||'')) return;
  const player=document.createElement('iframe');
  player.src=`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&start=${Math.max(0,Math.floor(start))}`;
  player.title=film.dataset.title || 'PanoVLN navigation visualization';
  player.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';
  player.referrerPolicy='strict-origin-when-cross-origin';player.allowFullscreen=true;
  document.querySelectorAll('.film iframe').forEach(other=>{
    // Removing a different player prevents simultaneous sound and GPU work.
    if(other.parentElement!==film) restoreCover(other.parentElement);
  });
  film.replaceChildren(player);player.focus();
}
const covers=new Map();
function restoreCover(film){film.replaceChildren(covers.get(film).cloneNode(true));}
document.querySelectorAll('.film').forEach(film=>{
  covers.set(film,film.firstElementChild.cloneNode(true));
  film.addEventListener('click',event=>{
    if(!event.target.closest('.film-cover')) return;
    document.querySelectorAll('.chapter').forEach(button=>{
      if(button.dataset.player!==film.id) return;
      const active=Number(button.dataset.start)===0;
      button.classList.toggle('active',active);
      button.setAttribute('aria-pressed',String(active));
    });
    playFilm(film);
  });
});
document.querySelectorAll('.chapter').forEach(button=>{
  button.addEventListener('click',()=>{
    button.parentElement.querySelectorAll('.chapter').forEach(item=>{
      item.classList.toggle('active',item===button);item.setAttribute('aria-pressed',String(item===button));
    });
    playFilm(document.getElementById(button.dataset.player),Number(button.dataset.start));
  });
});
const copy=document.getElementById('copy-citation');
copy?.addEventListener('click',async()=>{
 const status=document.getElementById('copy-status');
 try{await navigator.clipboard.writeText(document.getElementById('citation').textContent);status.textContent='BibTeX copied.';copy.textContent='Copied';setTimeout(()=>{copy.textContent='Copy';},2200);}
 catch{const range=document.createRange();range.selectNodeContents(document.getElementById('citation'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='Citation selected. Use your browser’s Copy command.';}
});
if(matchMedia('(hover:hover) and (prefers-reduced-motion:no-preference)').matches){
 document.querySelectorAll('.glass,.glass-control:not(.unavailable)').forEach(control=>{
  control.addEventListener('pointermove',event=>{const r=control.getBoundingClientRect();control.style.setProperty('--pointer-x',`${(event.clientX-r.left)/r.width*100}%`);control.style.setProperty('--pointer-y',`${(event.clientY-r.top)/r.height*100}%`);});
  control.addEventListener('pointerleave',()=>{control.style.removeProperty('--pointer-x');control.style.removeProperty('--pointer-y');});
 });
}
