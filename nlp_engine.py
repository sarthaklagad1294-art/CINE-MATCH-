"""NLP and recommendation engine for CineMatch.

The module is deliberately self-contained so it is easy to explain in a viva:
raw movie metadata is parsed, text tags are cleaned, TF-IDF vectors are built,
and a cosine-similarity matrix is cached for fast repeat launches.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Iterable

import joblib
import pandas as pd
from nltk.stem import SnowballStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:  # NLTK is optional at import time; the app still works offline.
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
except Exception:  # pragma: no cover - exercised only on broken NLTK installs
    stopwords = None
    word_tokenize = None


ENGINE_VERSION = "cinematch-tfidf-v3-genre-aware"

GENRE_ALIASES = {
    "horror": "Horror",
    "thriller": "Thriller",
    "thrillers": "Thriller",
    "action": "Action",
    "actions": "Action",
    "comedy": "Comedy",
    "comedies": "Comedy",
    "drama": "Drama",
    "dramatic": "Drama",
    "romance": "Romance",
    "romantic": "Romance",
    "fantasy": "Fantasy",
    "animation": "Animation",
    "animated": "Animation",
    "crime": "Crime",
    "mystery": "Mystery",
    "science fiction": "Science Fiction",
    "sci-fi": "Science Fiction",
    "scifi": "Science Fiction",
}


class MovieNotFoundError(LookupError):
    """Raised when a requested title is not in the catalog."""

    def __init__(self, title: str, suggestions: list[str] | None = None) -> None:
        self.title = title
        self.suggestions = suggestions or []
        message = f"Movie '{title}' was not found."
        if self.suggestions:
            message += f" Did you mean: {', '.join(self.suggestions)}?"
        super().__init__(message)


class MovieRecommender:
    """Load a movie catalog and expose title/text recommendation methods."""

    def __init__(
        self,
        movies_path: str | Path = "data/movies.csv",
        credits_path: str | Path = "data/credits.csv",
        model_dir: str | Path = "models",
        force_rebuild: bool = False,
    ) -> None:
        self.movies_path = Path(movies_path)
        self.credits_path = Path(credits_path)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.stemmer = SnowballStemmer("english")
        self.stop_words = self._load_stop_words()
        self.movies = self._load_and_prepare_data()
        self.vectorizer: TfidfVectorizer
        self.tfidf_matrix = None
        self.similarity_matrix = None
        self._load_or_build_model(force_rebuild=force_rebuild)
        self.title_to_index = {
            str(title).casefold(): index for index, title in self.movies["title"].items()
        }

    @staticmethod
    def _load_stop_words() -> set[str]:
        """Prefer NLTK's list, falling back to scikit-learn for offline starts."""
        if stopwords is not None:
            try:
                return set(stopwords.words("english"))
            except LookupError:
                pass
        return set(ENGLISH_STOP_WORDS)

    @staticmethod
    def _parse_json_like(value: Any) -> list[dict[str, Any]]:
        """Parse TMDB's JSON-like CSV cells without trusting arbitrary code."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return []
        return parsed if isinstance(parsed, list) else []

    @classmethod
    def _names(cls, value: Any, limit: int | None = None) -> list[str]:
        """Extract human-readable names from a TMDB list-of-dicts column."""
        names: list[str] = []
        for item in cls._parse_json_like(value):
            name = item.get("name")
            if name and name not in names:
                names.append(str(name))
            if limit and len(names) >= limit:
                break
        return names

    @classmethod
    def _director(cls, value: Any) -> str:
        """Return the first crew member whose job is Director."""
        for item in cls._parse_json_like(value):
            if str(item.get("job", "")).casefold() == "director":
                return str(item.get("name", ""))
        return ""

    def _load_and_prepare_data(self) -> pd.DataFrame:
        """Merge the movie and credits CSV files into the model-ready frame."""
        if not self.movies_path.exists() or not self.credits_path.exists():
            raise FileNotFoundError(
                "CineMatch data files are missing. Run data/generate_sample_data.py first."
            )

        movies = pd.read_csv(self.movies_path)
        credits = pd.read_csv(self.credits_path)
        if "movie_id" not in credits.columns and "id" in credits.columns:
            credits = credits.rename(columns={"id": "movie_id"})
        merged = movies.merge(
            credits,
            left_on="id",
            right_on="movie_id",
            how="left",
            suffixes=("", "_credits"),
        )
        required = ["id", "title", "overview"]
        merged = merged.dropna(subset=required).drop_duplicates(subset=["id"])
        for column in ("genres", "keywords", "cast", "crew"):
            if column not in merged.columns:
                merged[column] = "[]"

        merged["genres_names"] = merged["genres"].map(self._names)
        merged["keyword_names"] = merged["keywords"].map(self._names)
        merged["cast_names"] = merged["cast"].map(lambda value: self._names(value, limit=3))
        merged["director_name"] = merged["crew"].map(self._director)
        merged["overview"] = merged["overview"].fillna("").astype(str)
        merged["tags"] = merged.apply(self._combine_tags, axis=1)
        release_dates = merged["release_date"] if "release_date" in merged else pd.Series("", index=merged.index)
        ratings = merged["vote_average"] if "vote_average" in merged else pd.Series(0.0, index=merged.index)
        popularity = merged["popularity"] if "popularity" in merged else pd.Series(0.0, index=merged.index)
        merged["release_date"] = release_dates.fillna("").astype(str)
        merged["vote_average"] = pd.Series(pd.to_numeric(ratings, errors="coerce"), index=merged.index).fillna(0.0)
        merged["popularity"] = pd.Series(pd.to_numeric(popularity, errors="coerce"), index=merged.index).fillna(0.0)
        return merged.reset_index(drop=True)

    def _combine_tags(self, row: pd.Series) -> str:
        """Combine the explainable content features into one text field."""
        parts: Iterable[str] = [
            str(row.get("overview", "")),
            " ".join(row.get("genres_names", [])),
            " ".join(row.get("keyword_names", [])),
            " ".join(row.get("cast_names", [])),
            str(row.get("director_name", "")),
        ]
        return " ".join(part for part in parts if part)

    def preprocess_text(self, text: str) -> str:
        """Lowercase, tokenize, remove stopwords/punctuation, and stem text."""
        text = str(text or "").lower()
        if word_tokenize is not None:
            try:
                tokens = word_tokenize(text, preserve_line=True)
            except LookupError:
                tokens = re.findall(r"[a-zA-Z]+", text)
        else:
            tokens = re.findall(r"[a-zA-Z]+", text)
        cleaned = [
            self.stemmer.stem(token)
            for token in tokens
            if token.isalpha() and token not in self.stop_words and len(token) > 2
        ]
        return " ".join(cleaned)

    def _signature(self) -> str:
        digest = hashlib.sha256()
        digest.update(ENGINE_VERSION.encode("utf-8"))
        for path in (self.movies_path, self.credits_path):
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _load_or_build_model(self, force_rebuild: bool = False) -> None:
        """Load cached artifacts when the source signature still matches."""
        vectorizer_path = self.model_dir / "vectorizer.joblib"
        matrix_path = self.model_dir / "tfidf_matrix.joblib"
        similarity_path = self.model_dir / "similarity_matrix.joblib"
        metadata_path = self.model_dir / "metadata.json"
        signature = self._signature()
        cache_is_valid = (
            not force_rebuild
            and metadata_path.exists()
            and vectorizer_path.exists()
            and matrix_path.exists()
            and similarity_path.exists()
        )
        if cache_is_valid:
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                cache_is_valid = metadata.get("signature") == signature
            except (OSError, json.JSONDecodeError):
                cache_is_valid = False

        if cache_is_valid:
            self.vectorizer = joblib.load(vectorizer_path)
            self.tfidf_matrix = joblib.load(matrix_path)
            self.similarity_matrix = joblib.load(similarity_path)
            return

        self.vectorizer = TfidfVectorizer(
            tokenizer=str.split,
            preprocessor=None,
            token_pattern=None,
            lowercase=False,
            max_features=5000,
            ngram_range=(1, 2),
        )
        processed_tags = self.movies["tags"].map(self.preprocess_text)
        self.tfidf_matrix = self.vectorizer.fit_transform(processed_tags)
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
        joblib.dump(self.vectorizer, vectorizer_path)
        joblib.dump(self.tfidf_matrix, matrix_path)
        joblib.dump(self.similarity_matrix, similarity_path)
        metadata_path.write_text(
            json.dumps(
                {
                    "signature": signature,
                    "engine_version": ENGINE_VERSION,
                    "movie_count": len(self.movies),
                    "feature_count": int(self.tfidf_matrix.shape[1]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _resolve_title(self, title: str) -> tuple[int, str]:
        """Resolve exact or fuzzy title input to a catalog row."""
        query = str(title or "").strip()
        if not query:
            raise ValueError("Please enter a movie title.")
        exact_index = self.title_to_index.get(query.casefold())
        if exact_index is not None:
            return exact_index, str(self.movies.iloc[exact_index]["title"])
        titles = self.movies["title"].astype(str).tolist()
        matches = get_close_matches(query, titles, n=3, cutoff=0.62)
        if matches:
            matched = matches[0]
            return self.title_to_index[matched.casefold()], matched
        raise MovieNotFoundError(query, matches)

    @staticmethod
    def _year(value: Any) -> str:
        text = str(value or "")
        return text[:4] if text[:4].isdigit() else "—"

    def _row_to_dict(self, row: pd.Series) -> dict[str, Any]:
        """Convert an internal row to a JSON-safe movie record."""
        movie_id = int(row["id"])
        return {
            "id": movie_id,
            "title": str(row.get("title", "Untitled")),
            "overview": str(row.get("overview", "No overview available.")),
            "year": self._year(row.get("release_date", "")),
            "release_date": str(row.get("release_date", "")),
            "rating": round(float(row.get("vote_average", 0.0)), 1),
            "popularity": round(float(row.get("popularity", 0.0)), 1),
            "genres": list(row.get("genres_names", [])),
            "keywords": list(row.get("keyword_names", [])),
            "cast": list(row.get("cast_names", [])),
            "director": str(row.get("director_name", "")) or "Not listed",
            "poster_path": str(row.get("poster_path", "") or ""),
        }

    def _recommendation(self, index: int, score: float, matched_title: str | None = None) -> dict[str, Any]:
        result = self._row_to_dict(self.movies.iloc[index])
        result["similarity"] = round(float(score), 4)
        result["similarity_percent"] = round(float(score) * 100, 1)
        if matched_title:
            result["matched_title"] = matched_title
        return result

    @staticmethod
    def _safe_count(value: Any, default: int = 10) -> int:
        try:
            return max(1, min(int(value), 40))
        except (TypeError, ValueError):
            return default

    def _group_key(self, index: int) -> str:
        """Group offline chapter variants while keeping real TMDB rows independent."""
        row = self.movies.iloc[index]
        value = row.get("collection_key", "")
        return str(value) if value else f"movie-{row.get('id', index)}"

    @staticmethod
    def _explicit_genres(query: str) -> list[str]:
        """Extract genre words so they can act as search constraints, not filler."""
        normalized = re.sub(r"[^a-z0-9-]+", " ", query.casefold())
        found: list[str] = []
        for phrase, genre in sorted(GENRE_ALIASES.items(), key=lambda item: -len(item[0])):
            if re.search(rf"\b{re.escape(phrase)}\b", normalized) and genre not in found:
                found.append(genre)
        return found

    def recommend(self, title: str, n: int | str = 10) -> list[dict[str, Any]]:
        """Return top-N movies similar to a catalog title."""
        index, matched_title = self._resolve_title(title)
        count = self._safe_count(n)
        scores = list(enumerate(self.similarity_matrix[index]))
        scores.sort(key=lambda item: item[1], reverse=True)
        used_groups = {self._group_key(index)}
        results = []
        for movie_index, score in scores:
            group = self._group_key(movie_index)
            if movie_index == index or group in used_groups:
                continue
            used_groups.add(group)
            results.append(self._recommendation(movie_index, score, matched_title))
            if len(results) >= count:
                break
        return results

    def recommend_text(self, query_text: str, n: int | str = 10) -> list[dict[str, Any]]:
        """Return top-N movies that match a free-text viewing description."""
        query = str(query_text or "").strip()
        if not query:
            raise ValueError("Please describe what you want to watch.")
        processed = self.preprocess_text(query)
        if not processed:
            raise ValueError("Please use a little more descriptive language.")
        query_vector = self.vectorizer.transform([processed])
        scores = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        explicit_genres = self._explicit_genres(query)
        if explicit_genres:
            genre_overlap = self.movies["genres_names"].map(
                lambda genres: sum(genre in genres for genre in explicit_genres)
            ).to_numpy(dtype=float)
            # An explicit single genre is a hard constraint. For combined genre
            # searches, keep matching films and reward titles matching more terms.
            if len(explicit_genres) == 1:
                scores = scores.copy()
                scores[genre_overlap == 0] = -1.0
                primary_genre = self.movies["genres_names"].map(
                    lambda genres: bool(genres) and genres[0] == explicit_genres[0]
                ).to_numpy(dtype=float)
                scores = scores + primary_genre * 0.45
            scores = scores + (genre_overlap / len(explicit_genres)) * 0.35
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        count = self._safe_count(n)
        used_groups: set[str] = set()
        results = []
        for index, score in ranked:
            group = self._group_key(index)
            if group in used_groups:
                continue
            used_groups.add(group)
            results.append(self._recommendation(index, score))
            if len(results) >= count:
                break
        return results

    def get_movie(self, movie_id: int | str) -> dict[str, Any] | None:
        """Return a full movie record by numeric id."""
        try:
            numeric_id = int(movie_id)
        except (TypeError, ValueError):
            return None
        rows = self.movies[self.movies["id"] == numeric_id]
        return self._row_to_dict(rows.iloc[0]) if not rows.empty else None

    def list_movies(
        self,
        query: str = "",
        limit: int | str = 12,
        sort: str = "title",
    ) -> list[dict[str, Any]]:
        """List catalog summaries for autocomplete and the trending rail."""
        frame = self.movies
        query = str(query or "").strip().casefold()
        try:
            safe_limit = max(1, min(int(limit), 50))
        except (TypeError, ValueError):
            safe_limit = 12
        if query:
            frame = frame[frame["title"].astype(str).str.casefold().str.contains(query, regex=False)]
        if sort == "popular":
            frame = frame.sort_values(["popularity", "vote_average"], ascending=False)
        elif sort == "rating":
            frame = frame.sort_values(["vote_average", "popularity"], ascending=False)
        else:
            frame = frame.sort_values("title")
        return [self._row_to_dict(row) for _, row in frame.head(safe_limit).iterrows()]
