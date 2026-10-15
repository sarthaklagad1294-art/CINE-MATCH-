# CineMatch Delivery Checklist

## 1. Runnable Flask and NLP engine
- [x] Provide a clean Python 3.10+ Flask application with docstrings and comments.
- [x] Implement `nlp_engine.py` to load and merge movie/credits data, parse JSON-like fields, clean nulls/duplicates, combine overview/genres/keywords/top-3 cast/director into tags, preprocess text with NLTK-compatible tokenization/stopwords/stemming, vectorize with TF-IDF (`max_features=5000`, `ngram_range=(1,2)`), cache artifacts, and compute cosine similarity.
- [x] Expose title recommendations, free-text recommendations, fuzzy title matching, empty-input handling, and movie detail lookup.
- [x] Include a self-contained sample catalog of 200+ movies so the app runs without an external download, plus a TMDB download/replacement script.

## 2. Discovery experience
- [x] Implement a home page with a hero, title/free-text mode toggle, autocomplete suggestions, trending/popular rail, and responsive layout.
- [x] Render recommendation cards with poster, title, year, genres, rating, similarity percentage, and overview.
- [x] Implement genre filter, minimum-rating slider, similarity/rating/year sorting, loading spinner, hover motion, and mobile/desktop behavior.
- [x] Implement a movie detail modal showing poster, overview, cast, director, genres, and a More like this list.
- [x] Use TMDB poster URLs only when configured; otherwise render a reliable placeholder poster.
- [x] Implement an About page explaining TF-IDF and cosine similarity with a simple visual pipeline diagram.

## 3. Flask API and routing
- [x] Provide `GET /`, `GET /api/movies`, `GET /api/recommend`, `POST /api/recommend-text`, and `GET /api/movie/<id>`.
- [x] Return proper JSON error messages and status codes for missing, empty, invalid, or unknown requests.
- [x] Provide `GET /manus-routes.json` and an unauthenticated health endpoint for Preview/deployment checks.

## 4. Documentation, tests, and deployment
- [x] Pin dependencies in `requirements.txt` and document venv, install, NLTK setup, model caching, running, screenshots, algorithm explanation, sample evaluations for Avatar, The Dark Knight, and Toy Story, and Render/PythonAnywhere deployment.
- [x] Include `.env.example`, Dockerfile, and deployment-safe configuration.
- [x] Add tests covering engine loading, title/text recommendations, fuzzy matching, and error cases.
- [x] Run compile/import checks, pytest, API smoke tests, and Preview readiness checks; fix confirmed issues before checkpointing.
