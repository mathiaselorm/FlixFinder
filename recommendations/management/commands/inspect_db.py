
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from django.contrib.auth import get_user_model
from recommendations.models import Movie, Rating

User = get_user_model()

class Command(BaseCommand):
    help = "Print summary statistics of Users, Movies, and Ratings in the database."

    def handle(self, *args, **options):
        # Users
        total_users = User.objects.count()
        self.stdout.write(f"Total users: {total_users}")

        # Movies
        total_movies = Movie.objects.count()
        enriched_movies = Movie.objects.exclude(overview__isnull=True).exclude(overview="").count()
        unenriched_movies = total_movies - enriched_movies
        self.stdout.write(f"Total movies: {total_movies}")
        self.stdout.write(f"  Enriched movies (having overview): {enriched_movies}")
        self.stdout.write(f"  Unenriched movies: {unenriched_movies}")

        # Ratings
        total_ratings = Rating.objects.count()
        avg_rating_global = Rating.objects.aggregate(avg=Avg('score'))['avg']
        self.stdout.write(f"Total ratings: {total_ratings}")
        self.stdout.write(f"  Global average rating: {avg_rating_global:.2f}")

        # Top 5 movies by number of ratings
        top_movies = (
            Movie.objects.annotate(num_ratings=Count('ratings'))
            .order_by('-num_ratings')[:5]
        )
        self.stdout.write("\nTop 5 Movies by number of ratings:")
        for m in top_movies:
            self.stdout.write(f"  {m.title} (movielens_id={m.movielens_id}) - {m.num_ratings} ratings")

        # Bottom 5 movies by number of ratings (excluding 0)
        bottom_movies = (
            Movie.objects.annotate(num_ratings=Count('ratings'))
            .filter(num_ratings__gt=0)
            .order_by('num_ratings')[:5]
        )
        self.stdout.write("\nBottom 5 Movies by number of ratings (excluding 0):")
        for m in bottom_movies:
            self.stdout.write(f"  {m.title} (movielens_id={m.movielens_id}) - {m.num_ratings} ratings")

        # Users with most ratings
        top_users = (
            User.objects.annotate(num_ratings=Count('ratings'))
            .order_by('-num_ratings')[:5]
        )
        self.stdout.write("\nTop 5 Users by number of ratings:")
        for u in top_users:
            name = u.get_full_name() or u.email
            self.stdout.write(f"  {name} (id={u.id}) - {u.num_ratings} ratings")

        # Users with zero ratings
        zero_users = User.objects.annotate(num_ratings=Count('ratings')).filter(num_ratings=0).count()
        self.stdout.write(f"\nUsers with zero ratings: {zero_users}")

        self.stdout.write(self.style.SUCCESS("\nDatabase inspection completed."))

