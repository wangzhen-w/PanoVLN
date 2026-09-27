#!/usr/bin/env python3
"""Validate local assets and refuse to publish unfinished video embeds."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.players = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("src", "href", "poster"):
            if attrs.get(key):
                self.assets.append(attrs[key])
        if "film" in attrs.get("class", "").split():
            self.players.append((attrs.get("id", "unnamed"), attrs.get("data-video-id", "")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-pending-videos", action="store_true", help="Local previews only")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "docs"
    page = Page()
    page.feed((root / "index.html").read_text())
    errors = []
    for asset in page.assets:
        url = urlsplit(asset)
        if not url.scheme and not url.netloc and url.path:
            target = (root / unquote(url.path)).resolve()
            if not target.is_file():
                errors.append(f"Missing local asset: {asset}")
    pending = [name for name, value in page.players if not re.fullmatch(r"[A-Za-z0-9_-]{11}", value)]
    if pending and not args.allow_pending_videos:
        errors.append("Upload and verify videos before deployment: " + ", ".join(pending))
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Local assets verified; {len(page.players)} players, {len(pending)} pending uploads.")


if __name__ == "__main__":
    main()
