# recommendations/views.py

from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)

from recommendations.models import Genre, Movie, Watchlist, Rating
from recommendations.serializers import (
    MovieCardSerializer,
    MovieDetailSerializer,
    WatchlistSerializer,
    MovieRecommendationSerializer,
    MovieMiniSerializer,
    RatingSerializer,
)
from recommendations.utils import get_top_n_recommendations, recommend_based_on_genres


@extend_schema(
    summary="Genres List with top 10 movies",
    description=(
        "List all genres, each with its top 10 movies by average_rating. "
    ),
    responses={
        200: inline_serializer(
            name="GenreList",
            many=True,
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
                "slug": serializers.CharField(),
                "movies": MovieMiniSerializer(many=True)
            },
        )
    },
    tags=["Movies"],
)
class GenresView(APIView):
    """
    Returns each genre with a list of its top-10 movies (by average_rating).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Prefetch only the top 10 by average_rating per genre
        top10 = Prefetch(
            'movies',
            queryset=Movie.objects.order_by('-average_rating')[:10],
            to_attr='top10_movies'
        )
        genres = Genre.objects.prefetch_related(top10)
        payload = []
        for genre in genres:
            payload.append({
                'id':    genre.id,
                'name':  genre.name,
                'slug':  genre.slug,
                'movies': MovieMiniSerializer(genre.top10_movies, many=True).data
            })
        return Response(payload)


@extend_schema(
    summary="Genre detail",
    description=(
        "Given a genre slug, return three sections of movies:\n"
        "- Top 10 all-time\n"
        "- Top 10 released this year\n"
        "- Top 10 released last year"
    ),
    responses={
        200: inline_serializer(
            name="GenreDetailResponse",
            fields={
                "genre": serializers.CharField(),
                "sections": inline_serializer(
                    name="Section",
                    many=True,
                    fields={
                        "title": serializers.CharField(),
                        "movies": MovieCardSerializer(many=True)
                    }
                )
            },
        )
    },
    tags=["Movies"],
)
class GenreDetailView(APIView):
    """
    Return three sections of movies for that genre.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        today = date.today().year
        genre = get_object_or_404(
            Genre.objects.prefetch_related('movies'),
            slug=slug
        )
        qs = genre.movies.all()
        movies = [
            {
                'title': 'Top Rated',
                'movies': MovieMiniSerializer(qs.order_by('-average_rating')[:10], many=True).data
            },
            {
                'title': f'Popular {today}',
                'movies': MovieMiniSerializer(
                    qs.filter(release_date__year=today).order_by('-average_rating')[:10],
                    many=True
                ).data
            },
            {
                'title': f'Popular {today - 1}',
                'movies': MovieMiniSerializer(
                    qs.filter(release_date__year=today - 1).order_by('-average_rating')[:10],
                    many=True
                ).data
            },
        ]
        return Response({
            'genre': genre.name,
            'movies': movies
        })


@extend_schema(
    summary="Movie detail",
    description="Retrieve full details for one movie (by slug).",
    responses={200: MovieDetailSerializer},
    tags=["Movies"],
)
class MovieDetailView(generics.RetrieveAPIView):
    """
    Movie full detail, including:
    - genres
    - comments
    - whether it’s in the current user’s watchlist
    """
    queryset = Movie.objects.prefetch_related('genres', 'comments__user', 'watchlisted_by')
    serializer_class = MovieDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]


@extend_schema(
    summary="User watchlist",
    description=(
        "GET: list your watchlist\n"
        "POST: add a movie to watchlist\n"
        "DELETE: remove a movie"
    ),
    request=inline_serializer(
        name="WatchlistModify",
        fields={"movie_id": serializers.IntegerField()}
    ),
    responses={
        200: WatchlistSerializer(many=True),
        201: WatchlistSerializer,
        204: OpenApiResponse(description="Removed from watchlist")
    },
    tags=["Users"],
)
class WatchlistView(APIView):
    """
    Manage the current user’s watchlist.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = Watchlist.objects.filter(user=request.user) \
            .select_related('movie') \
            .prefetch_related('movie__genres')
        return Response(WatchlistSerializer(items, many=True).data)

    def post(self, request):
        movie = get_object_or_404(Movie, pk=request.data.get('movie_id'))
        item, _ = Watchlist.objects.get_or_create(user=request.user, movie=movie)
        return Response(WatchlistSerializer(item).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        item = get_object_or_404(
            Watchlist, user=request.user, movie_id=request.data.get('movie_id')
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Recommendations",
    description=(
        "If you’ve rated >5 movies → collaborative filtering (SVD),\n"
        "else → content-based (genres).\n"
        "Returns up to 10 `(movie, predicted_score)` pairs."
    ),
    responses={
        200: inline_serializer(
            name="Recommendation",
            many=True,
            fields={
                **MovieRecommendationSerializer().get_fields(),
                "predicted_score": serializers.FloatField()
            }
        )
    },
    tags=["Recommendations"],
)
class RecommendMoviesView(APIView):
    """
    - Collaborative if you have >5 ratings
    - Otherwise genre-based
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        count = Rating.objects.filter(user=user).count()
        if count > 5:
            recs = get_top_n_recommendations(user.id, n=10)
        else:
            recs = recommend_based_on_genres(user.id, n=10)

        # recs is a list of (Movie, score) tuples
        movies, scores = zip(*recs)  # unzip into two parallel tuples
        score_map = {movie.pk: score for movie, score in recs}

        serializer = MovieRecommendationSerializer(
            movies,
            many=True,
            context={'predicted_scores': score_map}
        )
        return Response(serializer.data)
    
    
    
@extend_schema_view(
    get=extend_schema(
        summary="List your ratings",
        description="Return all ratings the authenticated user has made.",
        responses={200: RatingSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Create a rating",
        description=(
            "Submit a rating for a movie.  "
            "Request body should be `{ \"movie\": <movie_id>, \"score\": <0.0–5.0> }`.  "
            "User is inferred from the auth token."
        ),
        request=RatingSerializer,
        responses={
            201: RatingSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    ),
    tags=["Ratings"],
)
class RatingListCreateView(generics.ListCreateAPIView):
    """
    get:
    List all ratings created by the current user.

    post:
    Create a new rating.  You only need to supply `movie` (its PK) and `score`.
    """
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return the current user's ratings
        return Rating.objects.filter(user=self.request.user).select_related("movie")

    def perform_create(self, serializer):
        # Attach the current user automatically
        serializer.save(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve a rating",
        description="Fetch a single rating by its ID (must belong to you).",
        responses={200: RatingSerializer},
    ),
    patch=extend_schema(
        summary="Update a rating",
        description="Change the `score` of one of your existing ratings.",
        request=RatingSerializer,
        responses={200: RatingSerializer},
    ),
    delete=extend_schema(
        summary="Delete a rating",
        description="Remove one of your ratings.",
        responses={204: OpenApiResponse(description="Deleted")},
    ),
    tags=["Ratings"],
)
class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    get:
    Retrieve one of your ratings.

    patch:
    Update its score (0.0–5.0).

    delete:
    Delete the rating.
    """
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Prevent access to other users' ratings
        return Rating.objects.filter(user=self.request.user)