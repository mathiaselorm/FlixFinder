# recommendations/management/commands/prune_movies.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from recommendations.models import Movie

class Command(BaseCommand):
    help = (
        "Prune your Movie table down to a manageable size by keeping only:\n"
        "  • Movies released within the last `recent_years`, ordered by average_rating,\n"
        "  • Then the all-time top-rated movies up to `max_count` total.\n"
        "Everything else will be deleted."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-count",
            type=int,
            default=1000,
            help="Total number of movies to keep (default: 1000).",
        )
        parser.add_argument(
            "--recent-years",
            type=int,
            default=1,
            help="How many years back to consider a movie “current” (default: 1).",
        )

    def handle(self, *args, **options):
        max_count     = options["max_count"]
        recent_years  = options["recent_years"]
        today         = timezone.now().date()
        cutoff_date   = today.replace(year=today.year - recent_years)

        # 1) Pick “current” movies
        current_qs = (
            Movie.objects
            .filter(release_date__gte=cutoff_date)
            .order_by("-average_rating")
        )
        current_ids = list(current_qs.values_list("id", flat=True)[:max_count])

        # 2) Fill the rest with all-time top-rated
        remaining = max_count - len(current_ids)
        if remaining > 0:
            top_qs = (
                Movie.objects
                .exclude(id__in=current_ids)
                .order_by("-average_rating")
            )
            top_ids = list(top_qs.values_list("id", flat=True)[:remaining])
        else:
            top_ids = []

        keep_ids = set(current_ids + top_ids)

        # 3) Delete everything else in one go
        to_delete_qs = Movie.objects.exclude(id__in=keep_ids)
        count_to_delete = to_delete_qs.count()

        if count_to_delete:
            with transaction.atomic():
                to_delete_qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Pruned {count_to_delete} movies. Kept {len(keep_ids)} total."
        ))











# # recommendations/management/commands/cleanup_unenriched_movies.py

# from django.core.management.base import BaseCommand
# from django.db.models import Q, Count
# from recommendations.models import Movie

# class Command(BaseCommand):
#     help = "Delete all Movie records that were not enriched (only have movielens_id, tmdb_id, imdb_id)."

#     def handle(self, *args, **options):
#         # Identify unenriched movies:
#         # - No overview (null or empty)
#         # - No poster_url
#         # - No trailer_url
#         # - No release_date
#         # - average_rating is zero
#         # - No genres associated
#         qs = (
#             Movie.objects
#             .annotate(genre_count=Count('genres'))
#             .filter(
#                 Q(overview__isnull=True) | Q(overview=''),
#                 poster_url__isnull=True,
#                 trailer_url__isnull=True,
#                 release_date__isnull=True,
#                 average_rating=0,
#                 genre_count=0,
#             )
#         )

#         count = qs.count()
#         if count == 0:
#             self.stdout.write(self.style.SUCCESS("No unenriched movies found."))
#             return

#         # Delete them
#         qs.delete()
#         self.stdout.write(self.style.SUCCESS(f"Deleted {count} unenriched movies."))
                
#         total = Movie.objects.count()
#         if total == 0:
#             self.stdout.write(self.style.SUCCESS("No movies remaining."))
#             return
#         self.stdout.write(self.style.SUCCESS("Cleanup completed."))
#         self.stdout.write(self.style.SUCCESS(f"Total movies remaining: {total}."))
        
        
        
        
# # recommendations/management/commands/dedupe_movies.py

# from django.core.management.base import BaseCommand
# from django.db.models import Count
# from recommendations.models import Movie

# class Command(BaseCommand):
#     help = "Remove duplicate Movie records (same tmdb_id or imdb_id), keeping the earliest entry."

#     def handle(self, *args, **options):
#         to_delete = set()

#         # 1) Find tmdb_id duplicates
#         dup_tmdb = (
#             Movie.objects
#             .values('tmdb_id')
#             .exclude(tmdb_id__isnull=True)
#             .annotate(c=Count('id'))
#             .filter(c__gt=1)
#             .values_list('tmdb_id', flat=True)
#         )
#         for tmdb_id in dup_tmdb:
#             movies = list(Movie.objects.filter(tmdb_id=tmdb_id).order_by('pk'))
#             # keep the first, delete the rest
#             for dup in movies[1:]:
#                 to_delete.add(dup.pk)

#         # 2) Find imdb_id duplicates
#         dup_imdb = (
#             Movie.objects
#             .values('imdb_id')
#             .exclude(imdb_id__isnull=True)
#             .annotate(c=Count('id'))
#             .filter(c__gt=1)
#             .values_list('imdb_id', flat=True)
#         )
#         for imdb_id in dup_imdb:
#             movies = list(Movie.objects.filter(imdb_id=imdb_id).order_by('pk'))
#             for dup in movies[1:]:
#                 to_delete.add(dup.pk)

#         # 3) Delete all collected duplicates
#         if not to_delete:
#             self.stdout.write(self.style.SUCCESS("No duplicate movies found."))
#             return

#         count = len(to_delete)
#         Movie.objects.filter(pk__in=to_delete).delete()
#         self.stdout.write(self.style.SUCCESS(f"Deleted {count} duplicate Movie records."))
