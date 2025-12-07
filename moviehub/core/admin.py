from django.contrib import admin
from .models import Genre, Movie, WatchlistItem, Review

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "tmdb_id", "slug")
    search_fields = ("name", "slug")

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "tmdb_id", "release_date", "vote_average", "featured")
    search_fields = ("title", "tmdb_id")
    list_filter = ("featured",)

@admin.register(WatchlistItem)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "tmdb_id", "added_at")
    search_fields = ("user__username", "title", "tmdb_id")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "tmdb_id", "rating", "created_at")
    search_fields = ("user__username",)
    list_filter = ("rating",)
