"""Flask web application for CineMatch."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory

from nlp_engine import MovieNotFoundError, MovieRecommender

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PLACEHOLDER_POSTER = "/static/images/placeholder-poster.svg"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        JSON_SORT_KEYS=False,
        MOVIES_PATH=BASE_DIR / "data" / "movies.csv",
        CREDITS_PATH=BASE_DIR / "data" / "credits.csv",
        MODEL_DIR=BASE_DIR / "models",
        TMDB_API_KEY=os.getenv("TMDB_API_KEY", "").strip(),
    )
    if test_config:
        app.config.update(test_config)

    app.extensions["recommender"] = MovieRecommender(
        movies_path=app.config["MOVIES_PATH"],
        credits_path=app.config["CREDITS_PATH"],
        model_dir=app.config["MODEL_DIR"],
    )

    def engine() -> MovieRecommender:
        return app.extensions["recommender"]

    @lru_cache(maxsize=256)
    def tmdb_poster_for_title(title: str) -> str:
        """Look up a TMDB poster only when a server-side key is configured."""
        api_key = app.config.get("TMDB_API_KEY", "")
        if not api_key:
            return PLACEHOLDER_POSTER
        try:
            response = requests.get(
                "https://api.themoviedb.org/3/search/movie",
                params={"api_key": api_key, "query": title, "include_adult": "false"},
                timeout=3,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            poster_path = next(
                (item.get("poster_path") for item in results if item.get("poster_path")),
                None,
            )
            return f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else PLACEHOLDER_POSTER
        except (requests.RequestException, ValueError, TypeError):
            return PLACEHOLDER_POSTER

    def enrich(movie: dict[str, Any]) -> dict[str, Any]:
        """Add a safe poster URL to an engine record."""
        enriched = dict(movie)
        poster_path = str(enriched.get("poster_path", "") or "")
        if poster_path.startswith("local:"):
            if app.config.get("TMDB_API_KEY", ""):
                enriched["poster_url"] = tmdb_poster_for_title(str(enriched.get("title", "")))
            else:
                cached_official = BASE_DIR / "static" / "images" / "posters" / f"{enriched.get('id')}.jpg"
                enriched["poster_url"] = (
                    f"/static/images/posters/{enriched['id']}.jpg"
                    if cached_official.exists()
                    else poster_path.removeprefix("local:")
                )
        elif poster_path.startswith("http"):
            enriched["poster_url"] = poster_path
        elif poster_path.startswith("/"):
            enriched["poster_url"] = f"{TMDB_IMAGE_BASE}{poster_path}"
        elif not app.config.get("TMDB_API_KEY", "") and enriched.get("id"):
            local_cover = BASE_DIR / "static" / "images" / "posters" / f"{enriched['id']}.svg"
            enriched["poster_url"] = f"/static/images/posters/{enriched['id']}.svg" if local_cover.exists() else PLACEHOLDER_POSTER
        else:
            enriched["poster_url"] = tmdb_poster_for_title(str(enriched.get("title", "")))
        return enriched

    def enrich_many(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [enrich(movie) for movie in movies]

    def parse_count() -> int:
        try:
            return max(1, min(int(request.args.get("n", 10)), 40))
        except (TypeError, ValueError):
            return 10

    @app.get("/")
    def home():
        trending = enrich_many(engine().list_movies(limit=10, sort="popular"))
        return render_template("index.html", trending=trending)

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/manus-routes.json")
    def route_manifest():
        return send_from_directory(BASE_DIR, "manus-routes.json", mimetype="application/json")

    @app.get("/_app/health")
    def health():
        return jsonify({"status": "ok", "service": "cinematch", "movies": len(engine().movies)})

    @app.get("/api/movies")
    def movie_list():
        query = request.args.get("q", "")
        sort = request.args.get("sort", "title")
        movies = engine().list_movies(query=query, limit=request.args.get("limit", 12), sort=sort)
        return jsonify({"movies": enrich_many(movies), "query": query})

    @app.get("/api/recommend")
    def recommend_by_title():
        title = request.args.get("title", "")
        try:
            recommendations = engine().recommend(title, n=parse_count())
            return jsonify({"query": title, "mode": "title", "recommendations": enrich_many(recommendations)})
        except ValueError as exc:
            return jsonify({"error": str(exc), "code": "empty_title"}), 400
        except MovieNotFoundError as exc:
            return jsonify({"error": str(exc), "code": "movie_not_found", "suggestions": exc.suggestions}), 404

    @app.post("/api/recommend-text")
    def recommend_by_text():
        payload = request.get_json(silent=True) or request.form
        query = str(payload.get("query", ""))
        try:
            recommendations = engine().recommend_text(query, n=payload.get("n", 10))
            return jsonify({"query": query, "mode": "text", "recommendations": enrich_many(recommendations)})
        except ValueError as exc:
            return jsonify({"error": str(exc), "code": "empty_query"}), 400

    @app.get("/api/movie/<int:movie_id>")
    def movie_detail(movie_id: int):
        movie = engine().get_movie(movie_id)
        if not movie:
            return jsonify({"error": "Movie not found.", "code": "movie_not_found"}), 404
        more_like_this = engine().recommend(movie["title"], n=6)
        movie["more_like_this"] = enrich_many(more_like_this)
        return jsonify(enrich(movie))

    @app.errorhandler(404)
    def not_found(error):  # noqa: ARG001
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found.", "code": "not_found"}), 404
        return render_template("index.html", trending=[]), 404

    @app.errorhandler(500)
    def internal_error(error):  # noqa: ARG001
        return jsonify({"error": "Something went wrong while preparing recommendations.", "code": "server_error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
