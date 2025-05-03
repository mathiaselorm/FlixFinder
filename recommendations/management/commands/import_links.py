import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from recommendations.models import Movie

class Command(BaseCommand):
    help = "Import MovieLens link mappings (movieId → imdbId, tmdbId), skipping any that already exist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="data/movielens/ml-latest-small",
            help="Path to the unzipped MovieLens 'ml-latest-small' directory"
        )

    def handle(self, *args, **options):
        ml_path = options["path"]
        links_file = os.path.join(ml_path, "links.csv")

        if not os.path.isfile(links_file):
            self.stderr.write(self.style.ERROR(f"Cannot find links.csv at {links_file}"))
            return

        created_count = 0
        skipped_count = 0

        self.stdout.write("Reading links.csv …")
        with open(links_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse movielens ID
                try:
                    ml_id = int(row["movieId"])
                except (KeyError, ValueError):
                    self.stderr.write(f"  ❌ Invalid or missing movieId, skipping row: {row!r}")
                    continue

                # Parse optional IDs
                imdb = row.get("imdbId") or None
                tmdb_raw = row.get("tmdbId")
                try:
                    tmdb = int(tmdb_raw) if tmdb_raw else None
                except ValueError:
                    tmdb = None

                # Try to get or create; never duplicates
                try:
                    with transaction.atomic():
                        movie, created = Movie.objects.get_or_create(
                            movielens_id=ml_id,
                            defaults={
                                "imdb_id": imdb,
                                "tmdb_id": tmdb,
                            }
                        )
                except Exception as e:
                    self.stderr.write(f"  ❌ Error upserting movielens_id={ml_id}: {e}")
                    continue

                if created:
                    self.stdout.write(
                        f"  ✅ Created Movie(id={movie.id}) "
                        f"movielens_id={ml_id}, imdb_id={imdb}, tmdb_id={tmdb}"
                    )
                    created_count += 1
                else:
                    self.stdout.write(f"  ⚪ Skipped existing Movie(id={movie.id}) movielens_id={ml_id}")
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Finished: {created_count} created, {skipped_count} skipped."
        ))
        self.stdout.write(self.style.SUCCESS("✅ import_links complete!"))
