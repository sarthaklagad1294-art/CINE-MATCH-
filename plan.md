# CineMatch Implementation Plan

## Scope and approach

CineMatch will be delivered as a runnable Flask application with a small, self-contained movie catalog so it works immediately without a TMDB download or API key. The project will also include an optional TMDB download script and a clear data replacement path. The recommendation engine will remain dataset-driven: the same TF-IDF vectorizer and cosine-similarity pipeline will power title recommendations and free-text discovery.

The build is intentionally modular for an engineering-college mini project:

- `app.py` owns Flask routes, API validation, poster URL handling, and JSON error responses.
- `nlp_engine.py` owns dataset parsing, preprocessing, model caching, fuzzy matching, recommendation scoring, and detail lookups.
- `data/` contains an out-of-the-box sample dataset (200+ movies) plus scripts/instructions for replacing it with TMDB 5000 files.
- `templates/` contains the home and methodology pages; `static/` contains the dark cinematic CSS, accessible modal, loading states, filters, autocomplete, and client-side rendering.
- `tests/` covers dataset loading, title recommendations, free-text recommendations, fuzzy matching, and error cases.

## Functional design

1. On startup, the engine loads `data/movies.csv` and `data/credits.csv`, merges them on movie id, parses JSON-like TMDB columns, normalizes text, and loads or rebuilds cached artifacts under `models/`.
2. Text is lowercased, tokenized with NLTK when its tokenizer data is available, cleaned with NLTK stopwords (with a deterministic fallback), and stemmed with `SnowballStemmer`.
3. A `TfidfVectorizer(max_features=5000, ngram_range=(1, 2))` creates the feature matrix; cosine similarity is cached with joblib and invalidated when source data or pipeline settings change.
4. The Flask API exposes title search, free-text recommendation, movie details, and health metadata. API responses contain poster, year, rating, genres, overview, similarity percentage, and explainable match metadata.
5. The browser provides a Netflix-inspired discovery surface: hero search, mode toggle, autocomplete, trending rail, filter/sort controls, movie cards, detail modal, and an About page with a visual NLP flow.
6. Posters use TMDB image URLs only when a key is configured; otherwise the UI uses a polished inline SVG/data placeholder and never breaks.

## Design direction

**Chosen movement: Cinematic editorial streaming UI.** The interface should feel like a film journal layered over a streaming catalog: deep ink surfaces, warm amber highlights, cool blue-violet accents, editorial typography, generous negative space, and restrained motion.

- **Core principles:** fast scanability, cinematic hierarchy, transparent recommendations, and graceful fallbacks.
- **Color philosophy:** near-black navy gives posters and content room to breathe; amber acts as the ownable CineMatch signal for action and confidence; violet-blue gradients imply discovery and machine intelligence without looking corporate.
- **Layout paradigm:** an asymmetric hero with a discovery panel, horizontally scrolling trend rails, and dense results that expand into a side-weighted modal rather than a generic centered dashboard.
- **Signature elements:** amber “match” rings, film-strip divider marks, and translucent glass panels with subtle grain.
- **Interaction philosophy:** every control should make discovery more specific; filters update instantly, cards lift on hover, and loading feedback keeps the search feeling deliberate.
- **Animation:** short ease-out lifts and opacity fades only; no looping decorative motion that competes with movie artwork.
- **Typography system:** `Space Grotesk` for display and UI labels, `Inter` for readable body text, with uppercase eyebrow labels and tabular numerals for scores.
- **Brand essence:** “Find the next film that feels like your kind of story.” Personality: curious, cinematic, precise.
- **Brand voice:** headlines are confident and concise; microcopy is helpful and conversational. Examples: “Describe the night you want to have.” and “A strong match, not just another title.”
- **Wordmark/mark:** a compact `CM` monogram shaped like two overlapping film frames, paired with the CineMatch wordmark.
- **Signature brand color:** CineMatch Amber `#F5B84B`.

## Project structure

```text
cinematch/
├── app.py
├── nlp_engine.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── README.md
├── plan.md
├── TODO.md
├── data/
│   ├── movies.csv
│   ├── credits.csv
│   ├── generate_sample_data.py
│   └── download_tmdb.py
├── models/
│   └── .gitkeep
├── static/
│   ├── css/styles.css
│   ├── js/app.js
│   └── images/placeholder-poster.svg
├── templates/
│   ├── index.html
│   └── about.html
└── tests/
    └── test_engine.py
```

## Build and delivery workflow

- Register Python diagnostics before source edits, then create the complete source tree and sample data.
- Install pinned Python dependencies in the sandbox, generate the model cache, and run the Flask server on the configured Preview port with `0.0.0.0` binding.
- Exercise `/`, `/manus-routes.json`, `/api/movies`, `/api/recommend`, `/api/recommend-text`, `/api/movie/<id>`, and `/_app/health` using HTTP requests; run the pytest suite and import/compile checks.
- Inspect the rendered Preview only if a concrete UI defect needs visual confirmation; otherwise rely on API and source checks.
- Add the container deployment contract and keep the Dockerfile production-ready for Render/PythonAnywhere guidance.
- Commit the completed project to the managed canonical branch after checks, preserving the generated model cache only if it is deterministic and small; the app can rebuild it on first run.

## Scope boundaries

- No login, database, payments, or user accounts are needed for this mini project.
- TMDB credentials remain optional and server-side; no secret is sent to browser code.
- The default app must work with the sample catalog and placeholder posters, while the README documents how to switch to TMDB data and configure posters.
