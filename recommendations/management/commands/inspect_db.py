import time
import logging
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from recommendations.models import Genre, Movie

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Fetch genres from TMDB and sync them into Genre and Movie.genres.
    
    1) Pull /genre/movie/list to seed your Genre table.
    2) For each Movie with a tmdb_id, GET /movie/{tmdb_id} and assign its genres.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.25,
            help="Seconds to sleep between TMDB requests (avoid rate‐limit).",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "TMDB_API_KEY", None)
        if not api_key:
            self.stderr.write(self.style.ERROR(
                "You must set TMDB_API_KEY in your Django settings."
            ))
            return

        session = requests.Session()
        base = "https://api.themoviedb.org/3"
        params = {"api_key": api_key, "language": "en-US"}

        # 1) Fetch all TMDB genres
        self.stdout.write("🔄 Fetching master genre list from TMDB…")
        resp = session.get(f"{base}/genre/movie/list", params=params)
        resp.raise_for_status()
        tmdb_genres = resp.json().get("genres", [])
        self.stdout.write(f"   • {len(tmdb_genres)} genres found")

        # Upsert into our Genre table
        for g in tmdb_genres:
            name = g["name"]
            slug = slugify(name)
            obj, created = Genre.objects.update_or_create(
                name__iexact=name,
                defaults={"name": name, "slug": slug},
            )
            if created:
                logger.info(f"Created genre '{name}'")
            else:
                logger.debug(f"Updated genre '{name}'")
        self.stdout.write(self.style.SUCCESS("✅ Genres table synced."))

        # 2) Walk through every Movie with a tmdb_id
        qs = Movie.objects.filter(tmdb_id__isnull=False)
        total = qs.count()
        self.stdout.write(f"🎥 Syncing genres for {total} movies…")

        for idx, movie in enumerate(qs, start=1):
            tmdb_id = movie.tmdb_id
            try:
                r = session.get(f"{base}/movie/{tmdb_id}", params=params, timeout=10)
                r.raise_for_status()
                data = r.json()
            except requests.RequestException as e:
                logger.error(f"[{idx}/{total}] TMDB fetch failed for tmdb_id={tmdb_id}: {e}")
                continue

            genre_list = data.get("genres", [])
            names = [g["name"] for g in genre_list]
            # Look up our Genre objects
            genres = list(Genre.objects.filter(name__in=names))
            if not genres and names:
                logger.warning(f"[{idx}/{total}] No local genres found for {names} on movie {movie.pk}")

            # Assign M2M
            with transaction.atomic():
                movie.genres.set(genres)

            self.stdout.write(f"[{idx}/{total}] {movie.title!r}: linked {len(genres)} genres")
            time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS("✅ All movie→genre links synchronized."))









# from django.core.management.base import BaseCommand
# from django.db.models import Count, Avg
# from django.contrib.auth import get_user_model
# from recommendations.models import Movie, Rating

# User = get_user_model()

# class Command(BaseCommand):
#     help = "Print summary statistics of Users, Movies, and Ratings in the database."

#     def handle(self, *args, **options):
#         # Users
#         total_users = User.objects.count()
#         self.stdout.write(f"Total users: {total_users}")

#         # Movies
#         total_movies = Movie.objects.count()
#         enriched_movies = Movie.objects.exclude(overview__isnull=True).exclude(overview="").count()
#         unenriched_movies = total_movies - enriched_movies
#         self.stdout.write(f"Total movies: {total_movies}")
#         self.stdout.write(f"  Enriched movies (having overview): {enriched_movies}")
#         self.stdout.write(f"  Unenriched movies: {unenriched_movies}")

#         # Ratings
#         total_ratings = Rating.objects.count()
#         avg_rating_global = Rating.objects.aggregate(avg=Avg('score'))['avg']
#         self.stdout.write(f"Total ratings: {total_ratings}")
#         self.stdout.write(f"  Global average rating: {avg_rating_global:.2f}")

#         # Top 5 movies by number of ratings
#         top_movies = (
#             Movie.objects.annotate(num_ratings=Count('ratings'))
#             .order_by('-num_ratings')[:5]
#         )
#         self.stdout.write("\nTop 5 Movies by number of ratings:")
#         for m in top_movies:
#             self.stdout.write(f"  {m.title} (movielens_id={m.movielens_id}) - {m.num_ratings} ratings")

#         # Bottom 5 movies by number of ratings (excluding 0)
#         bottom_movies = (
#             Movie.objects.annotate(num_ratings=Count('ratings'))
#             .filter(num_ratings__gt=0)
#             .order_by('num_ratings')[:5]
#         )
#         self.stdout.write("\nBottom 5 Movies by number of ratings (excluding 0):")
#         for m in bottom_movies:
#             self.stdout.write(f"  {m.title} (movielens_id={m.movielens_id}) - {m.num_ratings} ratings")

#         # Users with most ratings
#         top_users = (
#             User.objects.annotate(num_ratings=Count('ratings'))
#             .order_by('-num_ratings')[:5]
#         )
#         self.stdout.write("\nTop 5 Users by number of ratings:")
#         for u in top_users:
#             name = u.get_full_name() or u.email
#             self.stdout.write(f"  {name} (id={u.id}) - {u.num_ratings} ratings")

#         # Users with zero ratings
#         zero_users = User.objects.annotate(num_ratings=Count('ratings')).filter(num_ratings=0).count()
#         self.stdout.write(f"\nUsers with zero ratings: {zero_users}")

#         self.stdout.write(self.style.SUCCESS("\nDatabase inspection completed."))

