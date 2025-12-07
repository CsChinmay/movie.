from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

from . import views

app_name = "core"

urlpatterns = [
    # Home / main
    path("", views.home, name="home"),

    # Lists
    path("top-rated/", views.TopRatedListView.as_view(), name="top_rated"),
    path("upcoming/", views.UpcomingListView.as_view(), name="upcoming"),

    # Genres
    path("genres/", views.GenreListView.as_view(), name="genres_list"),
    path("genres/<int:genre_id>/", views.GenreDetailView.as_view(), name="genre_detail"),
    path("genres/slug/<slug:slug>/", views.GenreDetailView.as_view(), name="genre_detail_slug"),

    # Movie & person pages (JS-driven; TemplateView supplies the template)
    path("movie/<int:movie_id>/", TemplateView.as_view(template_name="core/movie_detail.html"), name="movie_detail"),
    path("person/<int:person_id>/", TemplateView.as_view(template_name="core/person_detail.html"), name="person_detail"),

    # Search (page)
    path("search/", TemplateView.as_view(template_name="core/search.html"), name="search"),

    # Auth / account
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="core:home"), name="logout"),

    # User profile (public profile URL)
    path("users/<str:username>/", views.user_profile, name="user_profile"),

    # API endpoints used by frontend JS
    path("api/movie/<int:movie_id>/", views.api_movie, name="api_movie"),
    path("api/suggestions/", views.search_suggestions, name="api_search_suggestions"),

    # Watchlist endpoints (page + AJAX toggles)
    path("watchlist/", views.watchlist_view, name="watchlist"),
    path("watchlist/toggle/", views.toggle_watchlist, name="toggle_watchlist"),
    path("watchlist/remove/", views.remove_watchlist, name="remove_watchlist"),

    # Reviews endpoints
    path("reviews/<int:tmdb_id>/", views.get_reviews, name="get_reviews"),
    path("reviews/add/", views.add_review, name="add_review"),
    path("reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),


    path("about/", views.about, name="about"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("contact/", views.contact, name="contact"),

]
