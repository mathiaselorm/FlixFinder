# # recommendations/management/commands/export_m2m.py
# import csv
# import os

# from django.core.management.base import BaseCommand
# from django.conf import settings
# from accounts.models import CustomUser
# from recommendations.models import Movie

# class Command(BaseCommand):
#     help = "Export Movie–Genre and User–PreferredGenre M2M tables to CSV"

#     def handle(self, *args, **options):
#         export_dir = os.path.join(settings.BASE_DIR, 'exports')
#         os.makedirs(export_dir, exist_ok=True)

#         # Movie <→> Genre
#         movie_genres_path = os.path.join(export_dir, 'movie_genres.csv')
#         with open(movie_genres_path, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerow(['movie_id', 'genre_id'])
#             through = Movie.genres.through
#             for rel in through.objects.all().values_list('movie_id', 'genre_id'):
#                 writer.writerow(rel)
#         self.stdout.write(self.style.SUCCESS(f'Exported Movie–Genre to {movie_genres_path}'))

#         # User <→> PreferredGenre
#         user_genres_path = os.path.join(export_dir, 'user_preferred_genres.csv')
#         with open(user_genres_path, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerow(['user_id', 'genre_id'])
#             through = CustomUser.preferred_genres.through
#             for rel in through.objects.all().values_list('customuser_id', 'genre_id'):
#                 writer.writerow(rel)
#         self.stdout.write(self.style.SUCCESS(f'Exported User–PreferredGenre to {user_genres_path}'))





import csv
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import CustomUser
from recommendations.models import Genre, Movie, Comment, Watchlist, Rating
from django.db.models import ForeignKey

class Command(BaseCommand):
    help = "Export key models to CSV files"

    def handle(self, *args, **kwargs):
        export_dir = os.path.join(settings.BASE_DIR, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        # Define models and filenames
        exports = [
            (CustomUser, 'users.csv'),
            (Genre, 'genres.csv'),
            (Movie, 'movies.csv'),
            (Comment, 'comments.csv'),
            (Watchlist, 'watchlists.csv'),
            (Rating, 'ratings.csv'),
        ]

        for model, fname in exports:
            path = os.path.join(export_dir, fname)
            self.stdout.write(f"→ Exporting {model._meta.db_table} → {fname}")
            self.export_model(model, path)
            self.stdout.write(self.style.SUCCESS(f"  done"))

    def export_model(self, model, path):
        # build header: use attname for FK, else f.name
        cols = []
        for f in model._meta.fields:
            if isinstance(f, ForeignKey):
                cols.append(f.attname)          # "user_id" instead of "user"
            else:
                cols.append(f.name)
        with open(path, 'w', newline='', encoding='utf-8') as csvf:
            writer = csv.writer(csvf)
            writer.writerow(cols)
            for obj in model.objects.all():
                row = []
                for col in cols:
                    row.append(getattr(obj, col))
                writer.writerow(row)
