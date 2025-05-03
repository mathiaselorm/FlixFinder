import csv
import os
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.utils.text import slugify

from recommendations.models import Movie

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Import up to 1000 enriched movies from Dataset/movies.csv, "
        "skipping those released before 2000 or missing a trailer_url."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="Dataset/movies.csv",
            help="Path to the exported movies.csv",
        )

    def handle(self, *args, **options):
        csv_path = options["path"]
        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"❌ File not found: {csv_path}"))
            return

        self.stdout.write(f"📖 Reading {csv_path}…")
        logger.info("Starting import_top_movies command")

        total_rows = 0
        skipped_date = skipped_year = skipped_trailer = 0
        movies = []

        # 1) Read & filter
        with open(csv_path, newline="", encoding="utf-8") as f:
            delimiter = "\t" if "\t" in f.read(1024) else ","
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                total_rows += 1

                # parse release_date
                raw_date = row.get("release_date", "").strip()
                try:
                    dt = datetime.strptime(raw_date, "%d/%m/%Y").date()
                except Exception:
                    skipped_date += 1
                    logger.debug(f"Row {total_rows}: invalid date '{raw_date}', skipping")
                    continue

                if dt.year < 2000:
                    skipped_year += 1
                    logger.debug(f"Row {total_rows}: year {dt.year}<2000, skipping")
                    continue

                trailer = row.get("trailer_url", "").strip()
                if not trailer:
                    skipped_trailer += 1
                    logger.debug(f"Row {total_rows}: missing trailer_url, skipping")
                    continue

                # parse average_rating
                try:
                    avg = float(row.get("average_rating", 0))
                except ValueError:
                    avg = 0.0
                    logger.debug(f"Row {total_rows}: invalid average_rating, defaulted to 0.0")

                movies.append({
                    "movielens_id":   row.get("movielens_id") or None,
                    "imdb_id":        row.get("imdb_id") or None,
                    "tmdb_id":        int(row["tmdb_id"]) if row.get("tmdb_id") else None,
                    "title":          row.get("title","").strip(),
                    "overview":       row.get("overview","").strip(),
                    "release_date":   dt,
                    "cast":           self.parse_cast(row.get("cast","")),
                    "language":       row.get("language","").strip(),
                    "poster_url":     row.get("poster_url") or None,
                    "trailer_url":    trailer,
                    "average_rating": avg,
                })

        self.stdout.write(f"🔢 Rows read: {total_rows}")
        self.stdout.write(
            f"   • Skipped by date parse: {skipped_date}\n"
            f"   • Skipped by year <2000: {skipped_year}\n"
            f"   • Skipped by missing trailer: {skipped_trailer}\n"
        )
        passed = len(movies)
        if not passed:
            self.stdout.write(self.style.WARNING("⚠️ No movies passed the filters."))
            logger.warning("No rows passed the filter criteria—aborting import.")
            return

        # 2) sort & limit
        movies.sort(key=lambda m: m["average_rating"], reverse=True)
        to_import = movies[:1000]
        self.stdout.write(f"🎯 {len(to_import)} movies selected for import (top by rating)")

        # 3) upsert into DB
        imported = created = updated = collisions = 0
        for idx, data in enumerate(to_import, start=1):
            mlid = str(data.pop("movielens_id"))
            base_slug = slugify(data["title"])

            with transaction.atomic():
                try:
                    obj, was_created = Movie.objects.update_or_create(
                        movielens_id=mlid,
                        defaults=data
                    )
                except IntegrityError:
                    # fallback if slug collision prevented update_or_create
                    obj, was_created = Movie.objects.get_or_create(
                        movielens_id=mlid,
                        defaults=data
                    )
                # enforce unique slug
                slug = obj.slug or base_slug
                if Movie.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                    new_slug = f"{base_slug}-{mlid}"
                    obj.slug = new_slug
                    obj.save(update_fields=["slug"])
                    collisions += 1
                    logger.warning(f"Slug collision for '{slug}', changed to '{new_slug}'")

            imported += 1
            if was_created:
                created += 1
                logger.debug(f"[{idx}/{len(to_import)}] Created Movie(id={obj.pk}, mlid={mlid})")
            else:
                updated += 1
                logger.debug(f"[{idx}/{len(to_import)}] Updated Movie(id={obj.pk}, mlid={mlid})")

            # progress every 100
            if imported % 100 == 0:
                self.stdout.write(f"  • {imported}/{len(to_import)} processed…")

        # 4) summary
        self.stdout.write(self.style.SUCCESS(
            f"✅ Import complete: {imported} total "
            f"({created} created, {updated} updated, {collisions} slug adjustments)"
        ))
        logger.info(
            f"import_top_movies finished: {imported} imported "
            f"({created} created, {updated} updated, {collisions} collisions)"
        )

    def parse_cast(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        if "|" in raw:
            parts = [p.strip() for p in raw.split("|") if p.strip()]
        else:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
        return parts or None
