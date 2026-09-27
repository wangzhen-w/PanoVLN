#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, re, json, html
parser = argparse.ArgumentParser(description="Extract PanoVLN LaTeX result tables, captions, authors and provenance into JSON and semantic HTML.")
parser.add_argument("--paper-root", type=Path, required=True, help="Directory containing main.tex, Sections/, and Figures/")
parser.add_argument("--asset-manifest", type=Path, default=Path("build/paper-content/figure-assets.json"))
parser.add_argument("--output-dir", type=Path, default=Path("build/paper-content"))
args = parser.parse_args()
PAPER = args.paper_root.resolve()
CONTENT = args.output_dir
CONTENT.mkdir(parents=True, exist_ok=True)
if not (PAPER / "main.tex").is_file():
 parser.error("--paper-root must contain main.tex")
def decomment(s): return re.sub(r'(?<!\\)%[^\n]*','',s)
def group(s,start):
 assert s[start]=='{', s[start:start+50]
 n=0
 for i in range(start,len(s)):
  if s[i]=='{' and (i==0 or s[i-1]!='\\'): n+=1
  if s[i]=='}' and s[i-1]!='\\':
   n-=1
   if n==0:return s[start+1:i],i+1
 raise ValueError('unbalanced brace')
def plain(s):
 s=decomment(s)
 s=re.sub(r'\\cite\w*\{[^}]*\}', '',s)
 replacements={r'\checkmark':'✓',r'\downarrow':'↓',r'\uparrow':'↑',r'\dagger':'†',r'\times':'×',r'\rightarrow':'→',r'\circ':'°',r'\%':'%',r'\,':' ',r'\;':' ',r'\quad':' ',r'\qquad':' ',r'\min':'min',r'\alpha':'α',r'\cdots':'…'}
 for a,b in replacements.items():s=s.replace(a,b)
 s=s.replace('$','').replace('~',' ').replace('--','–')
 s=re.sub(r'\\(?:textbf|emph|mathrm|texttt|mathbf)\s*\{([^{}]*)\}',r'\1',s)
 s=re.sub(r'\\[a-zA-Z]+', '',s)
 s=s.replace('{','').replace('}','').replace('^','')
 return re.sub(r'\s+',' ',s).strip()
def source_at(rel,pos,label=None):
 text=(PAPER/rel).read_text(); return {'path':str(rel),'line':text[:pos].count('\n')+1,**({'label':label} if label else {})}
specs=[
 ('simulation_main','Sections/4.exp.tex',['Method','Pano.','Odo.','Depth','S.RGB','R2R NE ↓','R2R OS ↑','R2R SR ↑','R2R SPL ↑','RxR NE ↓','RxR SR ↑','RxR SPL ↑','RxR nDTW ↑']),
 ('realworld_efficiency','Sections/4.exp.tex',['Method','Time (s) ↓','Speed (cm/s) ↑','Wait (%) ↓','Pauses ↓','Calls ↓','Latency (s) ↓']),
 ('sampling_ablation','Sections/4.exp.tex',['Sampling','NE ↓','OS ↑','SR ↑','SPL ↑']),
 ('cge_ablation','Sections/4.exp.tex',['Execution strategy','R2R NE ↓','R2R OS ↑','R2R SR ↑','R2R SPL ↑','RxR NE ↓','RxR SR ↑','RxR SPL ↑','RxR nDTW ↑']),
 ('spatial_encoder_ablation','Sections/4.exp.tex',['Extra encoder','R2R NE ↓','R2R OS ↑','R2R SR ↑','R2R SPL ↑','RxR NE ↓','RxR SR ↑','RxR SPL ↑','RxR nDTW ↑']),
 ('data_ablation','Sections/6.appendix.tex',['R2R','RxR','DAgger','PanoVLN data','R2R NE ↓','R2R OS ↑','R2R SR ↑','R2R SPL ↑','RxR NE ↓','RxR SR ↑','RxR SPL ↑','RxR nDTW ↑']),
 ('backbone_ablation','Sections/6.appendix.tex',['Backbone','R2R NE ↓','R2R OS ↑','R2R SR ↑','R2R SPL ↑','RxR NE ↓','RxR SR ↑','RxR SPL ↑','RxR nDTW ↑'])]
tables=[]
for name,rel,columns in specs:
 text=(PAPER/rel).read_text(); label='tab:'+name; lp=text.index('\\label{'+label+'}')
 begin=max(text.rfind('\\begin{table}',0,lp),text.rfind('\\begin{wraptable}',0,lp))
 tableend=text.index('\\end{tabular}',lp); block=text[begin:tableend]
 caption_start=block.index('\\caption{')+len('\\caption'); caption=plain(group(block,caption_start)[0])
 # Data rows begin at the first midrule after this table's header.
 data_start=text.index('\\midrule',lp)+len('\\midrule'); raw=text[data_start:tableend]
 raw=re.sub(r'\\(?:midrule|bottomrule)','',raw)
 rows=[]
 for chunk in re.split(r'\\\\',raw):
  chunk=decomment(chunk); chunk=re.sub(r'\\rowcolor\{[^}]+\}', '',chunk).strip()
  if not chunk: continue
  cells=chunk.split('&')
  if len(cells)!=len(columns):raise ValueError((name,len(cells),columns,chunk))
  values=[plain(c) for c in cells]
  bold=[r'\textbf' in c for c in cells]
  # Locate the first distinctive row token in the original file.
  first=re.sub(r'\\rowcolor\{[^}]+\}','',chunk).strip().splitlines()[0].strip()
  try:pos=text.index(first,data_start)
  except ValueError:pos=data_start
  rows.append({'cells':values,'bold':bold,'highlight':('Ours' in values[0] or 'PanoVLN' in values[0] or name=='data_ablation' and len(rows)==2),'source':source_at(rel,pos,label)})
 table={'id':name,'title':caption.split('.')[0],'caption':caption,'columns':columns,'rows':rows,'source':source_at(rel,begin,label)}
 tables.append(table)
 # HTML includes a semantic caption, column headers, and table body, ready to embed.
 out=[f'<div class="table-scroll"><table id="{name}">',f'<caption>{html.escape(caption)}</caption>','<thead><tr>'+''.join(f'<th scope="col">{html.escape(c)}</th>' for c in columns)+'</tr></thead>','<tbody>']
 for row in rows:
  out.append('<tr'+(' class="highlight"' if row['highlight'] else '')+'>')
  for i,(v,b) in enumerate(zip(row['cells'],row['bold'])):
   tag='th scope="row"' if i==0 else 'td'; close='th' if i==0 else 'td'; val=html.escape(v or '—');val=f'<strong>{val}</strong>' if b else val
   out.append(f'<{tag}>{val}</{close}>')
  out.append('</tr>')
 out+=['</tbody></table></div>'];(CONTENT/f'{name}.html').write_text('\n'.join(out))
# Numeric real-world plot data were checked against the visible labels in this source PDF.
# A changed PDF must be re-verified before exporting these transcribed values.
realworld_pdf = PAPER / "Figures/real_world_exp/realworld_exp.pdf"
if hashlib.sha256(realworld_pdf.read_bytes()).hexdigest() != "d6b0e18e3a371a1e946eff2af71ca0a65d81e8c6f2fc728f4781c9c2b9e37565":
 raise ValueError("The real-world performance figure changed. Re-check its bar labels before updating the SR/NE transcription in this exporter.")
methods=['NaVid','NaVILA','StreamVLN','JanusVLN','PanoVLN']
sr=[[60,40,0],[75,30,0],[80,55,15],[85,65,30],[100,95,80]]
ne=[[2.1,5.6,12.6],[1.4,4.7,10.7],[0.9,2.6,3.9],[0.7,2.3,3.3],[0.3,0.4,1.2]]
realworld={'id':'realworld_navigation','title':'Real-world navigation performance','caption':'20 shared instruction–route pairs per setting, without scene-specific fine-tuning. Success rate (%) and navigation error (m).','columns':['Method','Hallway SR ↑','Hallway NE ↓','Office SR ↑','Office NE ↓','Campus SR ↑','Campus NE ↓'],'rows':[{'cells':[m]+[str(v) for pair in zip(sr[i],ne[i]) for v in pair],'highlight':m=='PanoVLN','bold':[m=='PanoVLN']*7,'source':{'path':'Figures/real_world_exp/realworld_exp.pdf','page':1,'location':'Visible labels above bars in the SR and NE charts'}} for i,m in enumerate(methods)],'source':{'path':'Figures/real_world_exp/realworld_exp.pdf','page':1,'tex_path':'Sections/4.exp.tex','label':'fig:realworld_navigation','verification':'Extracted PDF labels and visually checked each bar against its method/setting legend.'}}
tables.insert(2,realworld)
# Every provided figure is retained; figures not referenced by the current TeX have explicit status.
figures=json.loads(args.asset_manifest.read_text())
tex_files=[PAPER/'main.tex']+sorted(p for p in (PAPER/'Sections').glob('*.tex') if not p.name.startswith('.'))
for fig in figures:
 refs=[]
 for file in tex_files:
  text=file.read_text(); path=fig['source_pdf']; occurrences=list(re.finditer(re.escape(path),text))
  for occ in occurrences:
   line=text[:occ.start()].count('\n')+1
   # Ignore comments that contain an unused placeholder path.
   lineprefix=text[text.rfind('\n',0,occ.start())+1:occ.start()]
   if '%' in lineprefix:continue
   end=next((m.start() for m in re.finditer(r'\\end\{(?:figure|wrapfigure|minipage)\}',text[occ.end():])),None)
   after=text[occ.end():occ.end()+end if end is not None else len(text)]
   cm=re.search(r'\\caption(?:of\{figure\})?(?:\[[^]]*\])?\{',after)
   caption=plain(group(after,cm.end()-1)[0]) if cm else None
   lm=re.search(r'\\label\{([^}]+)\}',after)
   refs.append({'path':str(file.relative_to(PAPER)),'line':line,'label':lm.group(1) if lm else None,'caption':caption})
 fig['references']=refs;fig['used_in_current_paper']=bool(refs)
 fig['caption']=next((r['caption'] for r in refs if r['caption']),None)
 if not fig['caption']:
  fig['caption']={'attention_analyze-main_attention_pair':'Paired panoramic attention visualization.','train_cost-train_cost_r2r':'Success rate versus the number of training samples on R2R-CE.'}.get(fig['id'],fig['id'].replace('-',' ').replace('_',' '))
  fig['caption_source']='Descriptive label for supplied, currently unreferenced figure; not a paper caption.'
main=(PAPER/'main.tex').read_text();title=plain(group(main,main.index('\\title{PanoVLN: Towards')+len('\\title'))[0]); abs_tex=(PAPER/'Sections/0.abs.tex').read_text();abstract=plain(re.sub(r'\\(?:begin|end)\{abstract\}','',abs_tex))
author_block = group(main, main.index('\\author{') + len('\\author'))[0]
authors_found = [{'name': name.strip(), 'affiliation': int(aff)} for name, aff in re.findall(r'([A-Z][A-Za-z -]*?)\$\^\{(\d+)\}\$', author_block)]
if len(authors_found) != 8:
 raise ValueError('Expected the eight-author PanoVLN release block; review the source author formatting before exporting.')
result={'title':title,'title_source':source_at('main.tex',main.index('\\title{PanoVLN: Towards')),'authors':authors_found,'affiliations':{'1':'Zhejiang University','2':'The University of Hong Kong'},'abstract':abstract,'summary':'PanoVLN is an RGB-only panoramic vision-and-language navigation framework. It combines longer-horizon action prediction, confidence-guided execution, decision-centric training routes, and fused semantic and geometric features without adding visual tokens.','summary_source':[{'path':'Sections/0.abs.tex','line':20},{'path':'Sections/4.exp.tex','line':180}],'highlights':[{'label':'R2R-CE success rate','value':77.3,'unit':'%','source':{'path':'Sections/4.exp.tex','label':'tab:simulation_main','method':'PanoVLN (Ours)','column':'R2R SR'}},{'label':'RxR-CE success rate','value':78.0,'unit':'%','source':{'path':'Sections/4.exp.tex','label':'tab:simulation_main','method':'PanoVLN (Ours)','column':'RxR SR'}},{'label':'Backbone','value':'4B','source':{'path':'Sections/4.exp.tex','line':183}},{'label':'RGB-only panoramas','value':'360°','source':{'path':'Sections/4.exp.tex','line':180}}],'tables':tables,'figures':figures,'source_notes':[{'severity':'inconsistency','detail':'Appendix prose claims Qwen3-VL-4B 76.2% SR on both benchmarks. Its actual table reports R2R 76.2 and RxR 75.7. Website tables preserve the tabulated numbers.','source':{'path':'Sections/6.appendix.tex','lines':[233,264]}},{'severity':'unreferenced_figure','detail':'Two supplied assets are not referenced by the current TeX: attention_analyze/main_attention_pair.pdf and train_cost/train_cost_r2r.pdf. They are still exported because the user requested every supplied figure.'},{'severity':'cross_figure_difference','detail':'The unreferenced training-cost figure labels StreamVLN R2R SR as 56.9, while the main benchmark table reports 56.4. The asset is preserved unchanged; headline and benchmark data use the main table.','source':{'path':'Figures/train_cost/train_cost_r2r.pdf','page':1}}],'paper_source':'main.tex and Sections/ within the supplied --paper-root','public_pdf':'assets/paper/PanoVLN.pdf'}
(CONTENT/'paper-content.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print('Exported',len(tables),'tables and',len(figures),'figures')
for t in tables: print(t['id'],len(t['rows']),'rows')
