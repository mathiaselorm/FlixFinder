
import csv
import os
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from django.contrib.auth import get_user_model
from recommendations.models import Movie, Rating

User = get_user_model()

class Command(BaseCommand):
    help = (
        "Import ratings.csv: create a user for each userId, "
        "map movieId → movielens_id, and import score & timestamp."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="data/movielens/ml-latest-small/ratings.csv",
            help="Path to the MovieLens ratings.csv file",
        )

    def handle(self, *args, **options):
        ratings_file = options["path"]
        if not os.path.isfile(ratings_file):
            return self.stderr.write(self.style.ERROR(f"File not found: {ratings_file}"))

        self.stdout.write(f"Reading ratings from {ratings_file} …")
        user_cache = {}
        imported = 0
        skipped = 0

        with open(ratings_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    uid = int(row["userId"])
                    mid = row["movieId"]
                    score = float(row["rating"])
                    ts = int(row["timestamp"])
                except (KeyError, ValueError):
                    skipped += 1
                    continue

                # 1️⃣ Ensure user exists
                if uid not in user_cache:
                    email = f"ml_{uid}@movielens.local"
                    full_name = f"MovieLens User {uid}"
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            "first_name": full_name,
                            "last_name": "",
                            "is_active": True,
                        },
                    )
                    if created:
                        user.set_unusable_password()
                        user.save()
                    user_cache[uid] = user
                user = user_cache[uid]

                # 2️⃣ Look up movie by movielens_id
                try:
                    movie = Movie.objects.get(movielens_id=str(mid))
                except Movie.DoesNotExist:
                    skipped += 1
                    continue

                # 3️⃣ Create or update rating
                created_at = datetime.fromtimestamp(ts, tz=dt_timezone.utc)
                with transaction.atomic():
                    Rating.objects.update_or_create(
                        user=user,
                        movie=movie,
                        defaults={
                            "score": score,
                            "created_at": created_at,
                            "updated_at": created_at,
                        },
                    )
                imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported {imported} ratings; skipped {skipped} rows."
        ))

        self.stdout.write(self.style.SUCCESS("✅ import_ratings complete!"))    