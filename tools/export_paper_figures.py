#!/usr/bin/env python3
from pathlib import Path
import argparse, json, shutil
import pypdfium2 as pdfium
from PIL import Image, ImageChops
parser = argparse.ArgumentParser(description="Render the supplied PanoVLN figure PDFs to high-resolution WebP and PNG, retaining each original PDF.")
parser.add_argument("--paper-root", type=Path, required=True, help="Directory containing main.tex and Figures/")
parser.add_argument("--output-dir", type=Path, default=Path("docs/assets/figures"))
parser.add_argument("--manifest", type=Path, default=Path("build/paper-content/figure-assets.json"))
parser.add_argument("--max-pixels", type=int, default=3200)
args = parser.parse_args()
PAPER = args.paper_root.resolve()
OUT = args.output_dir
if not (PAPER / "Figures").is_dir():
 parser.error("--paper-root must contain Figures/")
if args.max_pixels < 100:
 parser.error("--max-pixels must be at least 100")
OUT.mkdir(parents=True,exist_ok=True)
records=[]
for src in sorted((PAPER/'Figures').rglob('*.pdf')):
 if src.name.startswith('.'): continue
 rel=src.relative_to(PAPER)
 stem='-'.join(src.relative_to(PAPER/'Figures').with_suffix('').parts)
 if stem.endswith('-main'): stem=stem[:-5]
 doc=pdfium.PdfDocument(str(src)); page=doc[0]
 width,height=page.get_size(); scale=args.max_pixels/max(width,height)
 img=page.render(scale=scale).to_pil().convert('RGB')
 diff=ImageChops.difference(img,Image.new('RGB',img.size,'white')).convert('L')
 bbox=diff.point(lambda p: 255 if p>10 else 0).getbbox()
 if bbox:
  margin=24
  box=(max(0,bbox[0]-margin),max(0,bbox[1]-margin),min(img.width,bbox[2]+margin),min(img.height,bbox[3]+margin))
  img=img.crop(box)
 img.save(OUT/f'{stem}.png',optimize=True)
 img.save(OUT/f'{stem}.webp',quality=94,method=6)
 shutil.copy2(src,OUT/f'{stem}.pdf')
 records.append({'id':stem,'source_pdf':str(rel),'image':f'assets/figures/{stem}.webp','png':f'assets/figures/{stem}.png','pdf':f'assets/figures/{stem}.pdf','width':img.width,'height':img.height,'pages':len(doc),'webp_bytes':(OUT/f'{stem}.webp').stat().st_size})
 print(stem, img.size, flush=True)
 doc.close()
args.manifest.parent.mkdir(parents=True, exist_ok=True)
args.manifest.write_text(json.dumps(records, indent=2) + '\n')
