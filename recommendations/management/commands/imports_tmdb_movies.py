# recommendations/management/commands/enrich_tmdb_via_api.py

import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from recommendations.models import Movie, Genre
from recommendations.tmdb_client import TMDbClient  # your wrapper around TMDb REST

class Command(BaseCommand):
    help = "Enrich existing Movie records via TMDb API (skips movies already up-to-date)."

    def parse_date(self, date_str):
        """Parse YYYY-MM-DD or return None."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def handle(self, *args, **options):
        client = TMDbClient(settings.TMDB_API_KEY)

        # Preload TMDb genres once
        tmdb_genres = {g["id"]: g["name"] for g in client.get_genres().get("genres", [])}
        genre_map = {}
        for name in set(tmdb_genres.values()):
            genre_obj, _ = Genre.objects.get_or_create(name=name)
            genre_map[name] = genre_obj

        qs = Movie.objects.filter(tmdb_id__isnull=False)
        total = qs.count()
        self.stdout.write(f"Found {total} movies with tmdb_id to enrich…\n")
        updated = 0

        for idx, movie in enumerate(qs, start=1):
            tmdb_id = movie.tmdb_id
            if not tmdb_id:
                continue

            details = client.get_movie_details_by_tmdb_id(tmdb_id)
            if not details:
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] No details for TMDB {tmdb_id}, skipping."))
                continue

            # Gather TMDb data
            new_title = details.get("title")
            new_overview = details.get("overview")
            new_release = self.parse_date(details.get("release_date"))
            new_lang = details.get("original_language")
            new_poster = details.get("poster_path")
            new_poster_url = f"https://image.tmdb.org/t/p/w500{new_poster}" if new_poster else None
            new_avg = details.get("vote_average")

            # Prepare genre sets
            tmdb_genre_list = details.get("genres", [])
            tmdb_names = {g["name"] for g in tmdb_genre_list if "name" in g}
            current_names = set(movie.genres.values_list("name", flat=True))

            # Check if everything is already current
            if (
                movie.title == new_title and
                movie.overview == new_overview and
                movie.release_date == new_release and
                movie.language == new_lang and
                movie.poster_url == new_poster_url and
                float(movie.average_rating) == float(new_avg or 0) and
                current_names == tmdb_names and
                movie.trailer_url  # assume if trailer_url exists it's up-to-date
            ):
                self.stdout.write(f"[{idx}/{total}] Movie ID {movie.pk} already enriched; skipping.")
                continue

            # Begin update
            with transaction.atomic():
                fields = []
                if new_title and movie.title != new_title:
                    movie.title = new_title; fields.append("title")
                if new_overview is not None and movie.overview != new_overview:
                    movie.overview = new_overview; fields.append("overview")
                if new_release and movie.release_date != new_release:
                    movie.release_date = new_release; fields.append("release_date")
                if new_lang and movie.language != new_lang:
                    movie.language = new_lang; fields.append("language")
                if movie.poster_url != new_poster_url:
                    movie.poster_url = new_poster_url; fields.append("poster_url")
                if new_avg is not None and float(movie.average_rating) != float(new_avg):
                    movie.average_rating = new_avg; fields.append("average_rating")

                if fields:
                    movie.save(update_fields=fields)

                # Sync genres
                movie.genres.clear()
                for name in tmdb_names:
                    movie.genres.add(genre_map[name])

                # Fetch trailers
                videos = client.get_movie_videos(tmdb_id)
                trailer_url = None
                if videos:
                    trailers = [v for v in videos["results"] if v.get("type")=="Trailer" and v.get("site")=="YouTube"]
                    if trailers:
                        trailer_url = f"https://www.youtube.com/watch?v={trailers[0]['key']}"

                if trailer_url and trailer_url != movie.trailer_url:
                    movie.trailer_url = trailer_url
                    movie.save(update_fields=["trailer_url"])

                updated += 1

            self.stdout.write(f"[{idx}/{total}] Updated Movie pk={movie.pk}")

            # Rate-limit
            time.sleep(0.25)

        self.stdout.write(self.style.SUCCESS(f"\nDone. Enriched {updated} of {total} movies."))

