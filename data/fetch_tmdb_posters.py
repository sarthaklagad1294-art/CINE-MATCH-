"""Download official TMDB posters for the bundled catalog.

Usage:
    TMDB_API_KEY=your_key python data/fetch_tmdb_posters.py

The web app can use TMDB URLs live, but this script is useful when you want
local cached image files for faster loading or an offline demo. It matches by
title and release year, skips titles without a poster, and never overwrites
existing generated covers unless --replace is supplied.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "movies.csv"
POSTERS_DIR = ROOT / "static" / "images" / "posters"
API_URL = "https://api.themoviedb.org/3/search/movie"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache official TMDB movie posters locally.")
    parser.add_argument("--replace", action="store_true", help="Replace existing local cover files.")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N rows (0 means all).")
    args = parser.parse_args()

    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("TMDB_API_KEY is required. Add it to .env or export it before running this script.")

    POSTERS_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    session = requests.Session()
    session.headers.update({"User-Agent": "CineMatch/1.0 poster-cache"})
    downloaded = 0
    skipped = 0
    for row in rows[: args.limit or None]:
        target = POSTERS_DIR / f"{row['id']}.jpg"
        if target.exists() and not args.replace:
            skipped += 1
            continue
        params = {"api_key": api_key, "query": row["title"], "include_adult": "false", "page": 1}
        year = str(row.get("release_date", ""))[:4]
        if year.isdigit():
            params["year"] = year
        try:
            response = session.get(API_URL, params=params, timeout=12)
            response.raise_for_status()
            results = response.json().get("results", [])
            result = next((item for item in results if item.get("poster_path")), None)
            if not result:
                skipped += 1
                continue
            image = session.get(f"{IMAGE_URL}{result['poster_path']}", timeout=20)
            image.raise_for_status()
            target.write_bytes(image.content)
            downloaded += 1
            print(f"Downloaded {row['title']} -> {target.name}")
            time.sleep(0.05)
        except (requests.RequestException, ValueError) as error:
            print(f"Skipped {row['title']}: {error}")
    print(f"Finished: {downloaded} downloaded, {skipped} skipped.")


if __name__ == "__main__":
    main()
