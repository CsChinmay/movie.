from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from core import tmdb
from core.models import Genre, Movie

class Command(BaseCommand):
    help = "Sync genres from TMDb and optionally import popular/top-rated movies into local DB."

    def add_arguments(self, parser):
        parser.add_argument("--genres-only", action="store_true", help="Only sync genres")
        parser.add_argument("--import-popular-pages", type=int, default=0,
                            help="If >0, import that many pages of popular movies (20 per page).")
        parser.add_argument("--overwrite", action="store_true", help="Overwrite existing movie records (by movie_id)")

    def handle(self, *args, **options):
        genres_only = options["genres_only"]
        pages = options["import_popular_pages"]
        overwrite = options["overwrite"]

        self.stdout.write("Fetching genres from TMDb...")
        data = tmdb.get_genres()
        with transaction.atomic():
            for gid, name in data.items():
                g, created = Genre.objects.update_or_create(
                    tmdb_id=gid,
                    defaults={"name": name, "slug": slugify(name)},
                )
                if created:
                    self.stdout.write(f"Created genre: {name} ({gid})")

        self.stdout.write(self.style.SUCCESS("Genres synced."))

        if genres_only or pages <= 0:
            return

        self.stdout.write(f"Importing {pages} page(s) of popular movies from TMDb...")
        imported = 0
        for p in range(1, pages + 1):
            try:
                movies_data = tmdb.get_popular_movies(page=p).get("results", [])
            except Exception as e:
                self.stderr.write(f"Failed to fetch popular page {p}: {e}")
                continue

            with transaction.atomic():
                for m in movies_data:
                    tmdb_id = m["id"]
                    defaults = {
                        "title": m.get("title") or m.get("name") or "",
                        "overview": m.get("overview", ""),
                        "poster_path": m.get("poster_path"),
                        "backdrop_path": m.get("backdrop_path"),
                        "release_date": m.get("release_date") or None,
                        "tmdb_popularity": m.get("popularity", 0.0),
                        "tmdb_vote_average": m.get("vote_average", 0.0),
                    }
                    if overwrite:
                        Movie.objects.update_or_create(tmdb_id=tmdb_id, defaults=defaults)
                        imported += 1
                    else:
                        obj, created = Movie.objects.get_or_create(tmdb_id=tmdb_id, defaults=defaults)
                        if created:
                            imported += 1

                    # attach genres (if present)
                    genre_objs = []
                    for g in m.get("genre_ids", []):
                        try:
                            genre_objs.append(Genre.objects.get(tmdb_id=g))
                        except Genre.DoesNotExist:
                            pass
                    if genre_objs:
                        obj = Movie.objects.get(tmdb_id=tmdb_id)
                        obj.genres.add(*genre_objs)

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} movies."))
