'use strict';
// A small rounded-lens field: refraction is concentrated in the curved rim.
// The foreground is never filtered. Media lenses sample only their own poster.
(()=>{
 const ns='http://www.w3.org/2000/svg';
 const reduced=matchMedia('(prefers-reduced-transparency:reduce)');
 const chromium=/Chrome|Chromium|Edg\//.test(navigator.userAgent)&&!/OPR|CriOS/.test(navigator.userAgent);
 const maps=new Map();let nextId=0;
 const el=(name,attrs={})=>{const node=document.createElementNS(ns,name);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,v);return node;};
 const definitions=el('svg',{'aria-hidden':'true',width:0,height:0});
 definitions.style.cssText='position:absolute;pointer-events:none;overflow:hidden';
 const defs=el('defs');definitions.append(defs);document.body.append(definitions);
 function displacement(width,height){
  const key=width+'x'+height;if(maps.has(key))return maps.get(key);
  const radius=Math.min(width,height)/2,rim=Math.min(10,radius*.28);
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
  const context=canvas.getContext('2d');const data=context.createImageData(width,height);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
   const px=x+.5,py=y+.5;
   const cx=Math.max(radius,Math.min(width-radius,px));
   const cy=Math.max(radius,Math.min(height-radius,py));
   const dx=px-cx,dy=py-cy,len=Math.hypot(dx,dy),depth=radius-len;
   const t=Math.max(0,Math.min(1,depth/rim));
   // A smooth raised lip leaves the center clear and bends the boundary inward.
   const bend=depth>=0&&depth<rim?Math.sin(Math.PI*t)*.92:0;
   const i=(y*width+x)*4;
   data.data[i]=Math.round(128+(len?dx/len:0)*bend*127);
   data.data[i+1]=Math.round(128+(len?dy/len:0)*bend*127);
   data.data[i+2]=128;data.data[i+3]=255;
  }
  context.putImageData(data,0,0);const url=canvas.toDataURL();maps.set(key,url);return url;
 }
 function lens(width,height,strength,blur){
  const id='liquid-lens-'+nextId++;
  const filter=el('filter',{id,x:0,y:0,width,height,filterUnits:'userSpaceOnUse',primitiveUnits:'userSpaceOnUse','color-interpolation-filters':'sRGB'});
  filter.append(el('feImage',{href:displacement(width,height),x:0,y:0,width,height,preserveAspectRatio:'none',result:'lens-map'}));
  filter.append(el('feDisplacementMap',{in:'SourceGraphic',in2:'lens-map',scale:strength,xChannelSelector:'R',yChannelSelector:'G',result:'refracted'}));
  if(blur)filter.append(el('feGaussianBlur',{in:'refracted',stdDeviation:blur}));
  defs.append(filter);return {id,filter};
 }
 const records=new Map();
 function update(control){
  const media=control.classList.contains('video-start');
  if(media&&control.hidden)return;
  const width=Math.round(media?control.clientWidth:control.offsetWidth);
  const height=Math.round(media?control.clientHeight:control.offsetHeight);
  if(!width||!height)return;
  const frame=media?control.closest('.film-frame'):null;
  const fw=frame?.clientWidth||0,fh=frame?.clientHeight||0;
  const key=[width,height,fw,fh,reduced.matches].join(':');
  const old=records.get(control);if(old?.key===key)return;
  old?.filter?.remove();old?.surface?.remove();
  control.style.removeProperty('backdrop-filter');control.style.removeProperty('-webkit-backdrop-filter');
  records.set(control,{key});if(reduced.matches)return;
  if(media){
   const poster=frame.querySelector('video').getAttribute('poster');if(!poster)return;
   const optics=lens(width,height,16,0);
   const surface=el('svg',{viewBox:`0 0 ${width} ${height}`,'aria-hidden':'true',focusable:'false',class:'liquid-poster'});
   const group=el('g',{filter:`url(#${optics.id})`});
   group.append(el('image',{href:poster,x:(width-fw)/2,y:(height-fh)/2,width:fw,height:fh,preserveAspectRatio:'xMidYMid slice'}));
   surface.append(group);control.prepend(surface);records.set(control,{key,filter:optics.filter,surface});
  }else if(chromium){
   const navigation=control.classList.contains('masthead');
   const optics=lens(width,height,navigation?10:13,navigation?1.6:.3);
   control.style.backdropFilter=`url("#${optics.id}") ${navigation?"brightness(.65) ":""}saturate(115%)`;
   records.set(control,{key,filter:optics.filter});
  }
 }
 const controls=[...document.querySelectorAll('.glass,.glass-control')];
 const observer=new ResizeObserver(entries=>{
  const changed=new Set(entries.map(e=>e.target));
  for(const control of controls)if(changed.has(control)||changed.has(control.closest('.film-frame')))update(control);
 });
 controls.forEach(control=>{observer.observe(control);if(control.classList.contains('video-start'))observer.observe(control.closest('.film-frame'));update(control);});
 reduced.addEventListener('change',()=>controls.forEach(update));
 document.fonts.ready.then(()=>controls.forEach(update));
})();
