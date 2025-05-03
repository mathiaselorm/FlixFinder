import os
import pickle
from datetime import datetime

import pandas as pd
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models import Count, Q

from surprise import SVD, Dataset, Reader

from recommendations.models import Movie, Rating
from django.contrib.auth import get_user_model

User = get_user_model()

# Cache for loaded model
_cached_model = None

def _get_ratings_df():
    """
    Returns a DataFrame with columns ['userId', 'movieId', 'rating']
    from the Django database.
    """
    qs = Rating.objects.select_related('movie', 'user').values_list(
        'user__id', 'movie__movielens_id', 'score'
    )
    df = pd.DataFrame(list(qs), columns=['userId', 'movieId', 'rating'])
    return df


def train_and_save_model(n_factors=50, reg_all=0.02):
    """
    Trains an SVD model on all ratings and saves the pickle.
    """
    # 1. Load ratings into Surprise dataset
    df = _get_ratings_df()
    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(df[['userId', 'movieId', 'rating']], reader)
    trainset = data.build_full_trainset()

    # 2. Train SVD
    algo = SVD(n_factors=n_factors, reg_all=reg_all, random_state=42)
    algo.fit(trainset)

    # 3. Save locally
    model_dir = os.path.join(settings.BASE_DIR, 'recommendations', 'models')
    os.makedirs(model_dir, exist_ok=True)
    file_path = os.path.join(model_dir, 'svd_model.pkl')
    with open(file_path, 'wb') as f:
        pickle.dump(algo, f)

    # 4. Save to Django storage
    storage_path = 'recommendations/models/svd_model.pkl'
    data_bytes = pickle.dumps(algo)
    if default_storage.exists(storage_path):
        default_storage.delete(storage_path)
    default_storage.save(storage_path, ContentFile(data_bytes))

    # Reset cache
    global _cached_model
    _cached_model = None
    return algo


def load_model():
    """
    Loads the trained SVD model, caching it for future calls.
    """
    global _cached_model
    if _cached_model:
        return _cached_model

    # Try local filesystem first
    file_path = os.path.join(settings.BASE_DIR, 'recommendations', 'models', 'svd_model.pkl')
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            model = pickle.load(f)
    else:
        # Fallback to Django storage
        storage_path = 'recommendations/models/svd_model.pkl'
        with default_storage.open(storage_path, 'rb') as f:
            model = pickle.load(f)

    _cached_model = model
    return model


def predict_rating(user_id, movie_id):
    """
    Predict a rating for a given user and movie.
    Returns the estimated rating.
    """
    algo = load_model()
    # Surprise expects raw ids as they were trained (ints or strings)
    return algo.predict(str(user_id), str(movie_id)).est


def get_top_n_recommendations(user_id, n=10):
    """
    Returns top-n movie recommendations (Movie instances, estimated rating) for the user.
    """
    algo = load_model()

    # Candidate movies = those not rated by user
    rated = set(
        Rating.objects.filter(user_id=user_id).values_list('movie__id', flat=True)
    )
    candidates = Movie.objects.exclude(id__in=rated).values_list('id', flat=True)

    # Batch predict
    preds = [(mid, algo.predict(str(user_id), str(mid)).est) for mid in candidates]
    preds.sort(key=lambda x: x[1], reverse=True)

    top = preds[:n]
    # Fetch in bulk
    movie_ids = [mid for mid, _ in top]
    movies = Movie.objects.in_bulk(movie_ids)
    return [(movies[mid], rating) for mid, rating in top]


def recommend_based_on_genres(user_id, n=10):
    """
    Recommends movies based on user's preferred genres. Falls back to top-rated if none.
    """
    user = User.objects.get(id=user_id)
    prefs = list(user.preferred_genres.values_list('name', flat=True))

    if not prefs:
        qs = Movie.objects.order_by('-average_rating')[:n]
        return [(m, m.average_rating) for m in qs]

    # Filter movies matching any preferred genre
    qs = Movie.objects.filter(genres__name__in=prefs).distinct()
    # Annotate match count
    qs = qs.annotate(
        match_count=Count('genres', filter=Q(genres__name__in=prefs))
    ).order_by('-match_count', '-average_rating')[:n]
    return [(m, m.average_rating) for m in qs]
