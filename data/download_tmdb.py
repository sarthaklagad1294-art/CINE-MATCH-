"""Download TMDB 5000 CSV files from a local or public source.

Usage examples:
    python data/download_tmdb.py --movies /path/to/tmdb_5000_movies.csv --credits /path/to/tmdb_5000_credits.csv
    python data/download_tmdb.py --url https://example.com/tmdb_bundle.zip

The script intentionally keeps downloading explicit and optional; the app is
already runnable with the bundled sample files.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Install TMDB 5000 CSV files into data/.")
    parser.add_argument("--movies", type=Path, help="Path to tmdb_5000_movies.csv")
    parser.add_argument("--credits", type=Path, help="Path to tmdb_5000_credits.csv")
    parser.add_argument("--url", help="Optional URL to a zip containing both CSV files")
    args = parser.parse_args()

    if args.movies and args.credits:
        shutil.copyfile(args.movies, DATA_DIR / "movies.csv")
        shutil.copyfile(args.credits, DATA_DIR / "credits.csv")
        print("Installed TMDB files from local paths.")
        return
    if not args.url:
        parser.error("provide --movies and --credits, or provide --url")

    with tempfile.TemporaryDirectory() as temp_dir:
        archive = Path(temp_dir) / "tmdb.zip"
        urllib.request.urlretrieve(args.url, archive)
        with zipfile.ZipFile(archive) as bundle:
            names = {Path(name).name: name for name in bundle.namelist()}
            movies_name = names.get("tmdb_5000_movies.csv") or names.get("movies.csv")
            credits_name = names.get("tmdb_5000_credits.csv") or names.get("credits.csv")
            if not movies_name or not credits_name:
                raise RuntimeError("The archive must contain movies and credits CSV files.")
            bundle.extract(movies_name, temp_dir)
            bundle.extract(credits_name, temp_dir)
            shutil.copyfile(Path(temp_dir) / movies_name, DATA_DIR / "movies.csv")
            shutil.copyfile(Path(temp_dir) / credits_name, DATA_DIR / "credits.csv")
    print("Installed TMDB files from the supplied archive URL.")


if __name__ == "__main__":
    main()
