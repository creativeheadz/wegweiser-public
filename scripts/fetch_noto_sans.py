#!/usr/bin/env python3
"""
Fetches Noto Sans WOFF2 files (weights 400,500,600,700) from Google Fonts
and vendors them into app/static/fonts/noto-sans/.

- Subset: latin (unicode-range U+0000-00FF)
- Adds font-display: swap compatibility via our existing @font-face rules

Usage:
  python3 scripts/fetch_noto_sans.py
"""
import os
import re
import sys
import urllib.request
from pathlib import Path

GF_CSS_URL = "https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&display=swap"
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
}
WEIGHTS = [400, 500, 600, 700]

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = ROOT / "app/static/fonts/noto-sans"
CSS_PATH = Path("/tmp/noto_sans.css")


def fetch_css():
    req = urllib.request.Request(GF_CSS_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        css = r.read().decode("utf-8")
    CSS_PATH.write_text(css, encoding="utf-8")
    return css


def extract_urls(css: str):
    urls = {}
    # Split into @font-face blocks
    blocks = re.findall(r"@font-face\s*\{.*?\}", css, flags=re.S)
    for block in blocks:
        # Normalize whitespace to simplify matching
        b = re.sub(r"\s+", " ", block)
        for w in WEIGHTS:
            if (
                "font-style: normal" in b
                and f"font-weight: {w}" in b
                and "unicode-range: U+0000-00FF" in b  # latin subset
            ):
                m = re.search(r"url\((https:[^)]+\.woff2)\)", b)
                if m:
                    urls[w] = m.group(1)
    return urls


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {url}\n -> {dest}")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)


def main():
    print("Fetching Google Fonts CSS for Noto Sans …")
    css = fetch_css()
    urls = extract_urls(css)

    missing = [w for w in WEIGHTS if w not in urls]
    if missing:
        print("ERROR: Could not find URLs for weights:", missing)
        print(f"Saved CSS to {CSS_PATH} for debugging.")
        sys.exit(1)

    for w in WEIGHTS:
        dest = TARGET_DIR / f"noto-sans-{w}.woff2"
        download(urls[w], dest)

    print("All fonts downloaded.")
    print("Files:")
    for w in WEIGHTS:
        f = TARGET_DIR / f"noto-sans-{w}.woff2"
        print(" -", f, f"({f.stat().st_size} bytes)")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Failed:", e)
        sys.exit(1)

