# moviehub/core/views.py

import requests
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.template.loader import render_to_string
from django.views.generic import ListView
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from django.db import models

from .models import Genre, Movie, WatchlistItem, Review

User = get_user_model()

TMDB_BASE = "https://api.themoviedb.org/3"


def _tmdb_get(path: str, params: dict | None = None):
    """
    Helper that queries TMDb and returns parsed JSON (or raises).
    """
    params = params.copy() if params else {}
    params["api_key"] = getattr(settings, "TMDB_API_KEY", "")
    url = f"{TMDB_BASE}{path}"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _normalize_movie_from_tmdb(m):
    """
    Return a simple dict with guaranteed keys used by the template.
    Accepts either a TMDb result dict or a Django Movie model instance.
    """
    # if it's a model instance, try attribute access
    try:
        # detect model-ish by attribute
        if hasattr(m, "tmdb_id") or hasattr(m, "title"):
            return {
                "id": getattr(m, "tmdb_id", None) or getattr(m, "id", None),
                "title": getattr(m, "title", None) or getattr(m, "original_title", None),
                "poster_path": getattr(m, "poster_path", None),
                "poster_url": getattr(m, "poster_url", None),
                "release_date": getattr(m, "release_date", None),
                "vote_average": getattr(m, "vote_average", None),
            }
    except Exception:
        pass

    # else assume it's a TMDb dict-like
    return {
        "id": m.get("id") if isinstance(m, dict) else None,
        "title": m.get("title") or m.get("original_title") if isinstance(m, dict) else None,
        "poster_path": m.get("poster_path") if isinstance(m, dict) else None,
        "poster_url": m.get("poster_url") if isinstance(m, dict) else None,
        "release_date": m.get("release_date") if isinstance(m, dict) else None,
        "vote_average": m.get("vote_average") if isinstance(m, dict) else None,
    }


# -----------------------
# Home view
# -----------------------
def home(request):
    page = int(request.GET.get("page", 1))
    movies = []
    total_pages = 1
    try:
        tmdb = _tmdb_get("/movie/popular", params={"language": "en-US", "page": page})
        raw_movies = tmdb.get("results", [])
        total_pages = tmdb.get("total_pages", 1)
    except Exception:
        # fallback to local DB movies if you have them
        from .models import Movie  # local import to avoid circular at top
        raw_movies = list(Movie.objects.all().order_by("-created_at")[:24])

    # normalize all to guaranteed dicts
    movies = [_normalize_movie_from_tmdb(m) for m in raw_movies]

    genres = []  # optionally supply Genre list if template expects it
    years = [y for y in range(timezone.now().year, 1959, -1)]

    context = {
        "movies": movies,
        "page": page,
        "total_pages": total_pages,
        "genres": genres,
        "years": years,
    }
    return render(request, "core/home.html", context)

# -----------------------
# List / Genre Views (DB-backed list views)
# -----------------------
class TopRatedListView(ListView):
    model = Movie
    template_name = "core/top_rated.html"
    context_object_name = "movies"
    paginate_by = 24

    def get_queryset(self):
        return Movie.objects.all().order_by("-vote_average", "-vote_count")


class UpcomingListView(ListView):
    model = Movie
    template_name = "core/upcoming.html"
    context_object_name = "movies"
    paginate_by = 24

    def get_queryset(self):
        today = timezone.now().date()
        return Movie.objects.filter(release_date__gte=today).order_by("release_date", "title")


class GenreListView(ListView):
    model = Genre
    template_name = "core/genre.html"
    context_object_name = "genres"
    paginate_by = 50


class GenreDetailView(ListView):
    model = Movie
    template_name = "core/genre_detail.html"
    context_object_name = "movies"
    paginate_by = 24

    def get(self, request, genre_id=None, slug=None, *args, **kwargs):
        # Accept either numeric id (genre_id) or slug
        if genre_id:
            self.genre = get_object_or_404(Genre, pk=genre_id)
        elif slug:
            self.genre = get_object_or_404(Genre, slug=slug)
        else:
            return HttpResponseBadRequest("Missing genre identifier")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Movie.objects.filter(genres=self.genre).order_by("-release_date", "title")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["genre"] = self.genre
        return ctx


# -----------------------
# TMDb API wrapper endpoints for frontend
# -----------------------
def api_movie(request, movie_id: int):
    """
    Returns rich movie details (TMDb) for modal/detail page.
    """
    try:
        data = _tmdb_get(f"/movie/{movie_id}", params={"append_to_response": "videos,credits,images,similar", "language": "en-US"})
        return JsonResponse(data, safe=False)
    except requests.HTTPError as e:
        return JsonResponse({"error": "Failed to fetch movie from TMDb", "details": str(e)}, status=502)


def search_suggestions(request):
    """
    Simple search suggestions endpoint used by typeahead.
    Returns top 8 matches for a q=... query.
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"results": []})
    try:
        data = _tmdb_get("/search/movie", params={"query": q, "page": 1, "include_adult": False, "language": "en-US"})
        results = []
        for m in data.get("results", [])[:8]:
            results.append({
                "id": m.get("id"),
                "title": m.get("title"),
                "overview": m.get("overview"),
                "poster_path": m.get("poster_path"),
                "release_date": m.get("release_date"),
            })
        return JsonResponse({"results": results})
    except requests.HTTPError:
        return JsonResponse({"results": []}, status=502)


# -----------------------
# Watchlist views (page + AJAX)
# -----------------------
@login_required
def watchlist_view(request):
    items = WatchlistItem.objects.filter(user=request.user).order_by("-added_at")
    return render(request, "core/watchlist.html", {"items": items})


@login_required
def toggle_watchlist(request):
    """
    POST endpoint to toggle a movie in the user's watchlist.
    Expects: movie_id (int), title (optional), poster_path (optional)
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        movie_id = int(request.POST.get("movie_id") or request.POST.get("tmdb_id"))
    except Exception:
        return JsonResponse({"error": "Invalid movie id"}, status=400)

    title = request.POST.get("title", "")[:300]
    poster = request.POST.get("poster_path", "")[:255]

    obj, created = WatchlistItem.objects.get_or_create(user=request.user, tmdb_id=movie_id, defaults={"title": title, "poster_path": poster})
    if created:
        status = "added"
    else:
        obj.delete()
        status = "removed"

    return JsonResponse({"status": status, "movie_id": movie_id})


@login_required
def remove_watchlist(request):
    """
    Removes a watchlist item (POST).
    Accepts movie_id or id.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    movie_id = request.POST.get("movie_id") or request.POST.get("tmdb_id")
    if not movie_id:
        return JsonResponse({"error": "movie_id required"}, status=400)
    WatchlistItem.objects.filter(user=request.user, tmdb_id=movie_id).delete()
    return JsonResponse({"status": "removed", "movie_id": int(movie_id)})


# -----------------------
# Reviews endpoints (render partials)
# -----------------------
def get_reviews(request, tmdb_id: int):
    """
    Returns rendered HTML snippet for reviews for movie 'tmdb_id'.
    """
    reviews_qs = Review.objects.filter(tmdb_id=tmdb_id).order_by("-created_at")
    reviews = list(reviews_qs)
    # average rating
    avg = reviews_qs.aggregate(models.Avg("rating"))["rating__avg"] if reviews_qs.exists() else None

    html = render_to_string("core/_reviews.html", {"reviews": reviews, "avg_rating": avg, "tmdb_id": tmdb_id, "request": request})
    return JsonResponse({"html": html})


@login_required
def add_review(request):
    """
    Add or update a review. Expects POST with tmdb_id, text, rating (optional).
    Returns rendered reviews HTML in JSON.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        tmdb_id = int(request.POST.get("tmdb_id"))
    except Exception:
        return JsonResponse({"error": "Invalid tmdb_id"}, status=400)

    text = (request.POST.get("text") or "").strip()
    rating_raw = request.POST.get("rating")
    rating = None
    try:
        if rating_raw:
            rating = int(rating_raw)
            if rating < 0:
                rating = None
    except Exception:
        rating = None

    review, created = Review.objects.update_or_create(
        user=request.user,
        tmdb_id=tmdb_id,
        defaults={"text": text, "rating": rating, "updated_at": timezone.now()},
    )

    # return updated rendered reviews snippet
    return get_reviews(request, tmdb_id)


@login_required
def delete_review(request, review_id: int):
    """
    Delete a review owned by the current user.
    """
    if request.method not in ("POST", "DELETE"):
        return HttpResponseBadRequest("POST/DELETE required")
    review = get_object_or_404(Review, pk=review_id)
    if review.user != request.user:
        return HttpResponseForbidden("Not allowed")
    tmdb_id = review.tmdb_id
    review.delete()
    return get_reviews(request, tmdb_id)


# -----------------------
# Signup & simple auth helpers
# -----------------------
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("core:home"))
    else:
        form = UserCreationForm()
    return render(request, "core/signup.html", {"form": form})


# -----------------------
# User profile page
# -----------------------
def user_profile(request, username: str):
    profile_user = get_object_or_404(User, username=username)
    watchlist_items = WatchlistItem.objects.filter(user=profile_user).order_by("-added_at")[:48]
    reviews = Review.objects.filter(user=profile_user).order_by("-created_at")[:20]
    return render(request, "core/user_profile.html", {
        "profile_user": profile_user,
        "watchlist_items": watchlist_items,
        "reviews": reviews,
    })


def about(request):
    return render(request, "core/about.html", {})

def privacy(request):
    return render(request, "core/privacy.html", {})

def terms(request):
    return render(request, "core/terms.html", {})

def contact(request):
    return render(request, "core/contact.html", {})

