'use strict';
// Keep the independent players usable without overlapping sound.
document.querySelectorAll('video').forEach(video=>{
  const start=document.createElement('button');
  start.className='video-start glass-control';
  start.setAttribute('aria-label','Play '+(video.getAttribute('aria-label')||'video'));
  start.innerHTML='<img src="assets/icons/phosphor/regular/play.svg" alt="" width="28" height="28">';
  video.parentElement.append(start);
  video.controls=false;
  start.addEventListener('click',async()=>{
    video.controls=true;start.hidden=true;
    try{await video.play();video.focus();}
    catch{video.controls=false;start.hidden=false;start.focus();}
  });
  video.addEventListener('play',()=>{
    start.hidden=true;video.controls=true;
    document.querySelectorAll('video').forEach(other=>{if(other!==video) other.pause();});
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
  control.addEventListener('pointermove',event=>{if(matchMedia('(prefers-reduced-motion:reduce)').matches)return;const r=control.getBoundingClientRect();control.style.setProperty('--pointer-x',`${(event.clientX-r.left)/r.width*100}%`);control.style.setProperty('--pointer-y',`${(event.clientY-r.top)/r.height*100}%`);control.style.setProperty('--light-angle',`${Math.atan2(event.clientY-r.top-r.height/2,event.clientX-r.left-r.width/2)*180/Math.PI+90}deg`);});
  control.addEventListener('pointerleave',()=>{control.style.removeProperty('--pointer-x');control.style.removeProperty('--pointer-y');control.style.removeProperty('--light-angle');});
 });
}
