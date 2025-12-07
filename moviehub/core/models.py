from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=120, unique=True)
    tmdb_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Genre"
        verbose_name_plural = "Genres"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or str(self.pk or "")
            slug = base
            i = 1
            while Genre.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:genre_detail", kwargs={"genre_id": self.pk})


class Movie(models.Model):
    tmdb_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=300, blank=True)
    original_title = models.CharField(max_length=300, blank=True)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    backdrop_path = models.CharField(max_length=255, blank=True)
    release_date = models.DateField(null=True, blank=True)
    runtime = models.PositiveSmallIntegerField(null=True, blank=True)
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.PositiveIntegerField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name="movies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-release_date", "-vote_average"]
        verbose_name = "Movie"
        verbose_name_plural = "Movies"

    def __str__(self):
        return self.title or f"Movie {self.tmdb_id}"

    def get_absolute_url(self):
        return reverse("core:movie_detail", kwargs={"movie_id": self.tmdb_id})


class WatchlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_items")
    tmdb_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=300, blank=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "tmdb_id")
        ordering = ["-added_at"]
        verbose_name = "Watchlist item"
        verbose_name_plural = "Watchlist items"

    def __str__(self):
        return f"{self.user} — {self.title or self.tmdb_id}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    tmdb_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        unique_together = ("user", "tmdb_id")

    def __str__(self):
        return f"Review by {self.user} for {self.tmdb_id}"
