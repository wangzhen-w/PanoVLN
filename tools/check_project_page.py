#!/usr/bin/env python3
"""Validate local page assets and reject unresolved media sources before deployment."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
class Page(HTMLParser):
 def __init__(self):super().__init__();self.assets=[];self.videos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  self.assets.extend(a[k] for k in ('src','href','poster') if a.get(k))
  if tag=='video':self.videos.append(a.get('src',''))
def main():
 root=Path(__file__).resolve().parents[1]/'docs';p=Page();p.feed((root/'index.html').read_text());errors=[]
 for asset in p.assets:
  u=urlsplit(asset)
  if not u.scheme and not u.netloc and u.path and not (root/unquote(u.path)).is_file():errors.append('Missing local asset: '+asset)
 for src in p.videos:
  u=urlsplit(src)
  if u.scheme!='https' or u.netloc!='github.com' or not u.path.startswith('/user-attachments/assets/'):errors.append('Unresolved video: '+src)
 if errors:raise SystemExit('\n'.join(errors))
 print(f'Local assets verified; {len(p.videos)} native video players configured.')
if __name__=='__main__':main()
