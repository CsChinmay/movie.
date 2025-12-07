import requests, os
from django.conf import settings
from time import time
from django.http import JsonResponse
from . import tmdb

# Load API key
TMDB_KEY = os.getenv("TMDB_API_KEY") or getattr(settings, "TMDB_API_KEY", "")
BASE = "https://api.themoviedb.org/3"

# Small in-memory cache
_cache = {}
TTL = 60 * 5  # 5 minutes



def movie_api(request, movie_id):
    """
    Returns full movie details (JSON) from TMDb including videos & credits.
    """
    try:
        # tmdb._get should call /movie/{id} and accept params
        data = tmdb._get(f"/movie/{movie_id}", params={"append_to_response": "videos,credits,similar"})
    except Exception as e:
        return JsonResponse({"error": "Failed to fetch movie"}, status=500)

    if not data:
        return JsonResponse({"error": "Movie not found"}, status=404)
    return JsonResponse(data)



def _cache_get(key):
    item = _cache.get(key)
    if not item:
        return None
    ts, value = item
    if time() - ts > TTL:
        del _cache[key]
        return None
    return value


def _cache_set(key, value):
    _cache[key] = (time(), value)


def _get(path, params=None, use_cache=True):
    if params is None:
        params = {}

    params["api_key"] = TMDB_KEY
    params.setdefault("language", "en-US")

    key = f"{path}|{sorted(params.items())}"

    if use_cache:
        cached = _cache_get(key)
        if cached:
            return cached

    url = BASE + path
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    data = r.json()
    if use_cache:
        _cache_set(key, data)
    return data


# Main endpoints
def get_popular_movies(page=1):
    return _get("/movie/popular", {"page": page})


def earch_movies(query, page=1):
    return _get("/search/movie", {"query": query, "page": page, "include_adult": False})


def get_movie_details(movie_id):
    return _get(f"/movie/{movie_id}")


def get_movie_details(movie_id):
    return _get(
        f"/movie/{movie_id}",
        params={"append_to_response": "videos,credits,similar"}
    )


def get_person(person_id):
    return _get(f"/person/{person_id}")


def get_person_credits(person_id):
    return _get(f"/person/{person_id}/combined_credits")


def get_genres():
    data = _get("/genre/movie/list")
    return {g["id"]: g["name"] for g in data.get("genres", [])}
