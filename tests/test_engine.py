from pathlib import Path

import pytest

from nlp_engine import MovieNotFoundError, MovieRecommender


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def engine(tmp_path):
    return MovieRecommender(
        movies_path=ROOT / "data" / "movies.csv",
        credits_path=ROOT / "data" / "credits.csv",
        model_dir=tmp_path / "models",
    )


def test_catalog_has_more_than_two_hundred_movies(engine):
    assert len(engine.movies) >= 200
    assert engine.get_movie(1001)["title"] == "Avatar"


def test_title_recommendation_returns_scored_movies(engine):
    recommendations = engine.recommend("Avatar", n=5)
    assert len(recommendations) == 5
    assert all("similarity_percent" in movie for movie in recommendations)
    assert all(movie["title"] != "Avatar" for movie in recommendations)


def test_fuzzy_title_matching_is_exposed(engine):
    recommendations = engine.recommend("Avatr", n=2)
    assert recommendations
    assert recommendations[0]["matched_title"] == "Avatar"


def test_free_text_recommendation_uses_same_vectorizer(engine):
    recommendations = engine.recommend_text("space adventure with robots and emotional story", n=5)
    assert len(recommendations) == 5
    assert recommendations[0]["title"]
    assert recommendations[0]["similarity"] >= 0


def test_horror_query_returns_horror_and_distinct_films(engine):
    recommendations = engine.recommend_text(
        "horror thriller haunted house demon masked killer survival", n=8
    )
    assert len(recommendations) == 8
    assert any("Horror" in movie["genres"] for movie in recommendations)
    assert len({movie["title"] for movie in recommendations}) == len(recommendations)


def test_single_genre_queries_use_their_own_pools(engine):
    horror = engine.recommend_text("horror", n=8)
    thriller = engine.recommend_text("thriller", n=8)
    action = engine.recommend_text("action", n=8)
    assert all("Horror" in movie["genres"] for movie in horror)
    assert all("Thriller" in movie["genres"] for movie in thriller)
    assert all("Action" in movie["genres"] for movie in action)
    assert set(movie["title"] for movie in horror) != set(movie["title"] for movie in thriller)
    assert set(movie["title"] for movie in thriller) != set(movie["title"] for movie in action)


def test_empty_inputs_are_actionable(engine):
    with pytest.raises(ValueError, match="movie title"):
        engine.recommend("", n=5)
    with pytest.raises(ValueError, match="describe"):
        engine.recommend_text("", n=5)


def test_unknown_titles_return_suggestions_or_clear_error(engine):
    with pytest.raises(MovieNotFoundError) as error:
        engine.recommend("A Completely Unknown Film", n=5)
    assert "not found" in str(error.value).lower()


def test_detail_lookup_handles_missing_ids(engine):
    assert engine.get_movie(999999) is None
