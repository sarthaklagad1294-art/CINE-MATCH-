# CineMatch – Movie Recommendation System using NLP and Python

CineMatch is an engineering-college mini project that recommends movies from a title or a natural-language description. It uses a transparent content-based approach: movie metadata is combined into tags, cleaned with NLTK-compatible preprocessing, converted into TF-IDF vectors, and ranked with cosine similarity.

## What is included

The app runs out of the box with a bundled 375-row sample catalog spanning animation, drama, science fiction, action, thriller, and horror. It includes the requested anchor titles—**Avatar**, **The Dark Knight**, and **Toy Story**—plus dedicated horror titles such as **The Conjuring**, **A Quiet Place**, **Get Out**, **Alien**, and **Scream**, and dedicated thrillers such as **Se7en**, **Prisoners**, **Memento**, and **Nightcrawler**. Explicit single-genre searches are constrained to that genre and prioritize movies whose primary genre matches, so horror, thriller, and action searches produce meaningfully different result pools. Every bundled title has its own generated cinematic SVG cover under `static/images/posters/`, so the catalog never falls back to one repeated image. When `TMDB_API_KEY` is configured, live TMDB poster lookups take priority. The optional `data/download_tmdb.py` script explains how to replace the sample files with the official TMDB 5000 Movies + Credits CSVs.

The browser experience includes title search with autocomplete, free-text mood search, trending titles, full-catalog poster covers, similarity/rating/year sorting, genre and minimum-rating filters, responsive movie cards, a detail modal with cast/director/genres and “More like this”, and an About page with a viva-friendly NLP diagram.

## Project structure

```text
cinematch/
├── app.py                         # Flask routes and API error handling
├── nlp_engine.py                  # Parsing, preprocessing, TF-IDF and similarity cache
├── requirements.txt               # Pinned Python dependencies
├── .env.example                   # Optional TMDB key and runtime settings
├── Dockerfile                     # Render-compatible container entrypoint
├── data/
│   ├── movies.csv                 # Generated offline catalog
│   ├── credits.csv                # Generated cast/director metadata
│   ├── generate_sample_data.py    # Rebuild the offline catalog
│   ├── download_tmdb.py           # Optional TMDB file installer
│   └── fetch_tmdb_posters.py      # Cache official TMDB poster JPGs
├── models/                        # Joblib cache generated on first start
├── static/css/styles.css          # Dark cinematic responsive UI
├── static/js/app.js               # Search, filters, cards and modal behavior
├── static/images/placeholder-poster.svg
├── templates/index.html
├── templates/about.html
└── tests/test_engine.py
```

## Local setup

### 1. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Prepare NLTK resources (optional but recommended)

The engine has deterministic offline fallbacks for stopwords and tokenization, but these commands enable the full NLTK path:

```bash
python -m nltk.downloader punkt punkt_tab stopwords
```

### 3. Generate or replace the catalog

The sample files are committed for immediate use. To regenerate them:

```bash
python data/generate_sample_data.py
```

To use TMDB files copied from a dataset download:

```bash
python data/download_tmdb.py \
  --movies /path/to/tmdb_5000_movies.csv \
  --credits /path/to/tmdb_5000_credits.csv
```

After changing data, delete the files in `models/` (except `.gitkeep`) or let the signature check rebuild the cache automatically.

### 4. Configure official posters

```bash
cp .env.example .env
# Put a TMDB v3 API key in TMDB_API_KEY.
```

Create a free key at [TMDB API settings](https://www.themoviedb.org/settings/api). Restart Flask after adding it and CineMatch will use official TMDB poster URLs. To cache original poster JPGs locally for a faster/offline demo, run:

```bash
TMDB_API_KEY=your_tmdb_v3_key python data/fetch_tmdb_posters.py
```

The cache utility matches by title and release year, skips movies without artwork, and saves files as `static/images/posters/<id>.jpg`. Without a key or cache, CineMatch uses the bundled generated covers. Review [TMDB attribution requirements](https://www.themoviedb.org/faq/api#what-is-the-commercial-attribution-requirement) before publishing.

### 5. Run the app

```bash
PORT=5000 python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The first launch builds `models/vectorizer.joblib`, `models/tfidf_matrix.joblib`, `models/similarity_matrix.joblib`, and `models/metadata.json`; later launches reuse them.

## API reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Home page |
| GET | `/about` | NLP methodology page |
| GET | `/api/movies?q=dark&limit=6` | Autocomplete/catalog summaries |
| GET | `/api/recommend?title=Avatar&n=10` | Title-based recommendations |
| POST | `/api/recommend-text` | JSON body `{ "query": "space adventure with robots", "n": 10 }` |
| GET | `/api/movie/1001` | Full movie details and similar titles |
| GET | `/_app/health` | Deployment/Preview health response |
| GET | `/manus-routes.json` | Managed route manifest |

All API errors return JSON with an `error` message and a stable `code`. Title lookup also returns fuzzy suggestions when appropriate.

## How the algorithm works

1. **Load and merge:** `movies.csv` and `credits.csv` are joined on movie id. The engine keeps id, title, overview, genres, keywords, top three cast members, director, rating, popularity, and release date.
2. **Parse and clean:** TMDB-style list strings are parsed with `json.loads`/`ast.literal_eval`. Empty records and duplicate ids are removed.
3. **Create tags:** overview + genre names + keywords + cast + director become one explainable text field.
4. **Preprocess:** text is lowercased, tokenized, stripped of punctuation and stopwords, and stemmed with NLTK's SnowballStemmer. If NLTK corpora are not present, regex tokenization and scikit-learn's English stopword list keep the app runnable.
5. **Vectorize:** `TfidfVectorizer(max_features=5000, ngram_range=(1, 2))` turns each movie into a sparse numerical vector.
6. **Compare:** cosine similarity measures how close two movie vectors are. The largest scores become recommendations. A free-text query is transformed with the same vectorizer, so the model supports both titles and descriptions.
7. **Cache:** joblib stores the vectorizer, TF-IDF matrix, similarity matrix, and a source-data signature. The matrix is rebuilt only when the input files or engine version changes.

## Short evaluation examples

These are qualitative checks intended for a viva demonstration. With the bundled catalog, the anchor titles are expected to surface stories sharing their main signals:

| Input | Expected signal | What to discuss |
| --- | --- | --- |
| **Avatar** | space, aliens, survival, family, adventure | Content-based similarity is driven by shared metadata, not user profiles. |
| **The Dark Knight** | hero, villain, city, justice, crime | Genre and story keywords reinforce one another in the combined tag field. |
| **Toy Story** | animation, family, toys, friendship, childhood | The pipeline can match both genre and narrative concepts. |

Try these from the running app or with curl:

```bash
curl 'http://127.0.0.1:5000/api/recommend?title=Avatar&n=5'
curl -X POST 'http://127.0.0.1:5000/api/recommend-text' \
  -H 'Content-Type: application/json' \
  -d '{"query":"space adventure with robots and an emotional story","n":5}'
```

## Screenshots section

The responsive Preview is the source of truth for screenshots. Capture these two views after launching the app:

- **Discovery home:** hero search, orbit motif, trending rail, and the first recommendation grid after searching for `Avatar`.
- **Methodology page:** `/about`, showing the four-step pipeline and TF-IDF/cosine explanation.

The layout is intentionally built without a UI framework so the CSS and interaction choices are easy to present in a project report.

## Tests

```bash
pytest -q
python -m compileall app.py nlp_engine.py data tests
```

The test suite verifies catalog loading, title recommendations, fuzzy matching, free-text recommendations, details, and empty/unknown input behavior.

## Deployment guide

### Render (Docker)

1. Push this directory to a Git repository.
2. Create a new **Web Service** in Render and choose the repository.
3. Select **Docker**; Render will use the included `Dockerfile`.
4. Add the optional `TMDB_API_KEY` environment variable. Keep it server-side.
5. Use health check path `/_app/health`. The container honors Render's `PORT` value and binds to `0.0.0.0`.
6. Deploy. The Docker build regenerates the sample catalog and warms the model cache.

### PythonAnywhere

1. Create a Python 3.10+ web app using the manual Flask configuration.
2. Clone/upload the project, create a virtualenv, and install `requirements.txt`.
3. Run `python data/generate_sample_data.py` once, then warm the cache with `python -c "from nlp_engine import MovieRecommender; MovieRecommender()"`.
4. Point the WSGI file at `from app import app` and set the working directory to this project.
5. Configure the optional `TMDB_API_KEY` as an environment variable, reload the web app, and verify `/_app/health`.

## License and data note

The bundled sample records are for educational demonstration. If you replace them with TMDB data, follow the dataset provider's terms and keep API credentials out of source control.
