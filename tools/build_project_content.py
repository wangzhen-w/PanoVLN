#!/usr/bin/env python3
"""Render two curated main-result tables, preserving the complete research JSON.

Usage: python tools/build_project_content.py path/to/paper-content.json
The selection configuration contains only method/column names, never result values.
The HTML template must provide the benchmark-table and efficiency-table slots.
"""
from __future__ import annotations

import argparse
import copy
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def render_table(source: dict, selection: dict) -> str:
    """Select verified rows and columns by name and keep semantic table markup."""
    indices = [source["columns"].index(column) for column in selection["columns"]]
    by_method = {row["cells"][0]: row for row in source["rows"]}
    if len(by_method) != len(source["rows"]):
        raise ValueError(f"Duplicate method names in {source['id']}")
    rows = [by_method[method] for method in selection["methods"]]
    esc = html.escape
    title = esc(selection["title"])
    parts = [
        f'<div class="table-wrap" tabindex="0" role="region" aria-label="{title}">',
        f'<table><caption class="visually-hidden">{title}</caption><thead><tr>',
        *[f'<th scope="col">{esc(source["columns"][i])}</th>' for i in indices],
        '</tr></thead><tbody>',
    ]
    for row in rows:
        if len(row["cells"]) != len(source["columns"]):
            raise ValueError(f"Unexpected cell count in {source['id']}")
        parts.append('<tr class="ours">' if row.get("highlight") else '<tr>')
        for position, index in enumerate(indices):
            value = esc(str(row["cells"][index]))
            if row.get("bold", [False] * len(row["cells"]))[index]:
                value = f'<strong>{value}</strong>'
            if position == 0:
                parts.append(f'<th scope="row">{value}</th>')
            else:
                parts.append(f'<td>{value}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div>')
    return ''.join(parts)


def inject(page: str, identifier: str, content: str) -> str:
    """Replace one explicit slot, allowing classes and either attribute order."""
    opening = rf'(<div\b[^>]*\bid="{re.escape(identifier)}"[^>]*>)'
    marked = opening + rf'.*?(</div>\s*<!-- end {re.escape(identifier)} -->)'
    matches = list(re.finditer(marked, page, flags=re.S))
    if len(matches) == 1:
        return re.sub(marked, lambda match: match[1] + content + match[2], page, flags=re.S)
    if len(matches) > 1:
        raise ValueError(f"Duplicate {identifier} slots")
    empty = opening + r'\s*</div>'
    if len(list(re.finditer(empty, page))) != 1:
        raise ValueError(f"Missing or unmarked {identifier} slot; refusing to write an incomplete page")
    return re.sub(empty, lambda match: match[1] + content + f'</div><!-- end {identifier} -->', page)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', type=Path)
    parser.add_argument('--site', type=Path, default=ROOT / 'docs')
    parser.add_argument('--curation', type=Path, default=Path(__file__).with_name('project-page-curation.json'))
    args = parser.parse_args()
    data = json.loads(args.content.read_text())
    selections = json.loads(args.curation.read_text())["tables"]
    sources = {table["id"]: table for table in data["tables"]}
    page_path = args.site / 'index.html'
    page = page_path.read_text()
    for selection in selections:
        page = inject(page, selection["slot"], render_table(sources[selection["source_id"]], selection))
    # Keep all paper tables, figures and source notes for provenance/downloads.
    safe = copy.deepcopy({key: data[key] for key in
                         ['title', 'authors', 'affiliations', 'summary', 'tables', 'figures', 'source_notes']})
    for figure in safe['figures']:
        figure.pop('png', None)  # The site distributes WebP previews and original PDFs.
    assets = args.site / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    page_path.write_text(page)
    (assets / 'research-data.json').write_text(json.dumps(safe, ensure_ascii=False, indent=2) + '\n')
    print(f'Rendered {len(selections)} main-result tables; retained {len(data["tables"])} source tables and {len(data["figures"])} source figures in research-data.json')


if __name__ == '__main__':
    main()
