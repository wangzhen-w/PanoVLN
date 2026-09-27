#!/usr/bin/env python3
"""Render paper-content.json into the static project page (no browser JS needed)."""
import argparse, json, re, html
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('content',type=Path);p.add_argument('--site',type=Path,default=Path(__file__).resolve().parents[1]/'docs');args=p.parse_args()
data=json.loads(args.content.read_text());page=args.site/'index.html';s=page.read_text();esc=html.escape

def table(t,indices=None,rows=None):
 indices=indices or list(range(len(t['columns'])))
 out='<div class="table-wrap" tabindex="0" role="region" aria-label="'+esc(t['title'])+'"><table><caption class="visually-hidden">'+esc(t['title'])+'</caption><thead><tr>'
 out+=''.join('<th scope="col">'+esc(t['columns'][i])+'</th>' for i in indices)+'</tr></thead><tbody>'
 for r in (rows or t['rows']):
  out+='<tr'+(' class="ours"' if r['highlight'] else '')+'>'
  for j,i in enumerate(indices):
   tag='th' if j==0 else 'td';val=esc(r['cells'][i]);val='<strong>'+val+'</strong>' if r['bold'][i] else val
   out+='<'+tag+(' scope="row"' if j==0 else '')+'>'+val+'</'+tag+'>'
  out+='</tr>'
 return out+'</tbody></table></div>'

def inject(ident,value):
 global s
 pattern=r'(<div\b[^>]*\bid="'+re.escape(ident)+r'"[^>]*>).*?(</div><!-- end '+re.escape(ident)+r' -->)'
 if re.search(pattern,s,flags=re.S):s=re.sub(pattern,lambda m:m[1]+value+m[2],s,flags=re.S)
 else:s=re.sub(r'(<div\b[^>]*\bid="'+re.escape(ident)+r'"[^>]*>)</div>',lambda m:m[1]+value+'</div><!-- end '+ident+' -->',s)
main=data['tables'][0];selected=[r for r in main['rows'] if r['cells'][0] in ('StreamVLN','JanusVLN','DualVLN','AwareVLN','PanoVLN† (Ours)','PanoVLN (Ours)')]
inject('benchmark-table',table(main,[0,7,8,10,11],selected))
all_tables=''
for t in data['tables']:
 caption=t['caption'].replace('predictor from ;','predictor from BridgeVLN;').replace('Val-Unseen.Our','Val-Unseen. Our')
 all_tables+='<h3 class="table-title">'+esc(t['title'])+'</h3>'+table(t)+'<p class="table-note">'+esc(caption)+'</p>'
inject('all-tables',all_tables)
titles={'teaser-teaser':'Panoramic navigation at a glance','action_horizon':'Action horizon','attention_analyze-appendix_attention_gallery':'Attention across the panorama','attention_analyze-main_attention_pair':'Paired attention analysis','dataset_turn':'Where routes turn','datasource_ablation':'Training data and scale','navigation_cases-r2r_navigation':'Simulation navigation cases I','navigation_cases-rxr_navigation':'Simulation navigation cases II','navigation_cases-realworld_navigation':'Navigation beyond simulation','navigation_cases-realworld_navigation_appendix':'Real-world rollouts','position_uncertainty-position_uncertainty':'When to observe again','real_world_exp-realworld_exp':'Real-world performance','train_cost-train_cost_r2r':'Training cost and success'}
figs=[]
for f in data['figures']:
 if f['id'] in ('model_architecture-model_architecture','data_pipeline-data_pipeline'):continue
 title=titles.get(f['id'],f['id'].replace('_',' '));note='Additional supplied figure.' if not f.get('used_in_current_paper',True) else f['caption']
 if f['id']=='train_cost-train_cost_r2r':note+=' This supplied plot reports a different StreamVLN SR from the main table; use the main table for the benchmark comparison.'
 figs.append('<figure class="figure'+(' tall' if f['height']>f['width'] else '')+'"><a href="'+esc(f['pdf'])+'" aria-label="Open '+esc(title)+' as PDF"><img src="'+esc(f['image'])+'" width="'+str(f['width'])+'" height="'+str(f['height'])+'" alt="'+esc(f['caption'])+'" loading="lazy"></a><figcaption>'+esc(title)+'<small>'+esc(note)+'</small></figcaption></figure>')
inject('figure-gallery',''.join(figs));page.write_text(s)
# Keep provenance useful without publishing machine-specific paths.
safe={k:data[k] for k in ['title','authors','affiliations','summary','tables','figures','source_notes']}
for f in safe['figures']: f.pop('png', None)
(args.site/'assets'/'research-data.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2)+'\n')
print(f'Rendered {len(data["tables"])} tables and {len(data["figures"])} figures')
