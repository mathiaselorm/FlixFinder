# recommendations/views.py

from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, viewsets
from rest_framework.decorators import action
from django.db.models import Prefetch, Count
from rest_framework.views import APIView
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
    OpenApiParameter,
)

from recommendations.models import Genre, Movie, Watchlist, Rating
from recommendations.serializers import (
    MovieCardSerializer,
    MovieDetailSerializer,
    WatchlistSerializer,
    MovieRecommendationSerializer,
    MovieMiniSerializer,
    RatingSerializer,
    CommentSerializer,
    MovieWatchlistSerializer,
    RatingMiniSerializer
    

)
from recommendations.utils import get_top_n_recommendations, recommend_based_on_genres


@extend_schema(
    summary="Search Movies",
    description=(
        "Search for movies by title (case-insensitive substring).\n\n"
        "Returns up to 50 matching movies."
    ),
    parameters=[
        OpenApiParameter(
            name="q",
            type=str,
            description="Search term to match against movie titles",
            required=True,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={
        200: MovieMiniSerializer(many=True),
        400: OpenApiResponse(description="Missing or empty `q` parameter"),
    },
    tags=["Movies"],
)
class MovieSearchView(generics.ListAPIView):
    """
    GET /api/movies/search/?q=<term>
    """
    serializer_class = MovieMiniSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"detail": "Query parameter `q` is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # filter & order
        qs = Movie.objects.filter(title__icontains=q).order_by()[:50]
        
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


@extend_schema(
    summary="Genres List with rotating movie batches",
    description=(
        "List all genres, each with a batch of 10 movies by average_rating. "
        "Each call advances to the next batch of 10 (wrapping around)."
    ),
    responses={
        200: inline_serializer(
            name="RotatingGenreList",
            many=True,
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
                "slug": serializers.CharField(),
                "movies": MovieMiniSerializer(many=True),
            },
        )
    },
    tags=["Movies"],
)
class GenresView(APIView):
    """
    Returns each genre with a “rotating” list of up to 10 movies.
    On each request (or each refresh), it will advance to the next 10‐movie slice.
    Once you reach the end of the list it wraps back to the start.
    """
    permission_classes = [permissions.AllowAny]

    BATCH_SIZE = 10
    CACHE_KEY = "genre_{genre_pk}_offset"
    CACHE_TIMEOUT = None

    def get(self, request):
        payload = []
        # We want to know total count per genre to wrap around; annotate helps
        genres = Genre.objects.annotate(total_movies=Count('movies'))
        for genre in genres:
            total = genre.total_movies
            # no movies → just empty list
            if total == 0:
                batch = []
            else:
                # fetch our current offset from cache (default 0)
                cache_key = self.CACHE_KEY.format(genre_pk=genre.pk)
                offset = cache.get(cache_key, 0)

                # grab the next slice by average_rating
                qs = genre.movies.order_by('-average_rating')
                batch = list(qs[offset: offset + self.BATCH_SIZE])

                # compute next offset and wrap
                next_offset = offset + self.BATCH_SIZE
                if next_offset >= total:
                    next_offset = 0

                # store for next time
                cache.set(cache_key, next_offset, timeout=self.CACHE_TIMEOUT)

            serializer = MovieMiniSerializer(batch, many=True, context={'request': request})
            payload.append({
                "id":     genre.id,
                "name":   genre.name,
                "slug":   genre.slug,
                "movies": serializer.data,
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
                "movies": inline_serializer(
                    name="Movies",
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



@extend_schema_view(
    retrieve=extend_schema(
        summary="Retrieve Movie Detail",
        description="Fetch full details for a single movie (genres, cast, comments, watchlist status).",
        responses={200: MovieDetailSerializer},
        tags=["Movies"],
    ),
    comment=extend_schema(
        summary="Post a Comment",
        description="Authenticated users can post a new comment on this movie.",
        request=CommentSerializer,
        responses={201: CommentSerializer},
        tags=["Movies"],
    ),
    rate=extend_schema(
        summary="Rate a Movie",
        description="Authenticated users can create or update their rating for this movie.",
        request=inline_serializer(
            name="RateMovieRequest",
            fields={
                "score": serializers.DecimalField(
                    max_digits=3, decimal_places=1,
                    help_text="Your rating 0.0–5.0"
                )
            }
        ),
        responses={200: RatingMiniSerializer},
        tags=["Movies"],
    ),
    watchlist=extend_schema(
        summary="Toggle Watchlist",
        description=(
            "POST: Add this movie to the authenticated user's watchlist. No request body needed.\n"
            "\nDELETE: Removies this movie from authenticated user's watchlist. No request body needed."
        ),
        request=None,  # No body needed for POST/DELETE
        responses={
            201: MovieWatchlistSerializer,
            204: OpenApiResponse(description="Removed from watchlist"),
        },
        tags=["Movies"],
    ),
)
class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
    Return full movie detail (by slug).

    comment:
    POST a new comment.

    rate:
    POST to create/update a rating.

    watchlist:
    POST to add to watchlist; DELETE to remove.
    """
    queryset = Movie.objects.prefetch_related(
        'genres', 'comments__user', 'watchlisted_by'
    )
    serializer_class = MovieDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='comments'
    )
    def comment(self, request, slug=None):
        movie = self.get_object()
        if not Rating.objects.filter(user=request.user, movie=movie).exists():
            return Response(
                {"detail": "You must rate the movie before commenting."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, movie=movie)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="rate",
    )
    def rate(self, request, slug=None):
        movie = self.get_object()

        # 1️⃣ Build serializer input, including the movie PK
        data = {
            "movie": movie.pk,
            "score": request.data.get("score")
        }

        # 2️⃣ Delegate validation to RatingSerializer
        serializer = RatingSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # 3️⃣ Upsert: either update existing or create new
        rating_obj, created = Rating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={"score": serializer.validated_data["score"]},
        )

        # 4️⃣ Return the (fresh) rating through the same serializer
        out = RatingMiniSerializer(rating_obj)
        return Response(out.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='watchlist'
    )
    def watchlist(self, request, slug=None):
        movie = self.get_object()
        if request.method == 'POST':
            item, _ = Watchlist.objects.get_or_create(
                user=request.user, movie=movie
            )
            return Response(MovieWatchlistSerializer(item).data, status=status.HTTP_201_CREATED)
        else:
            item = get_object_or_404(
                Watchlist, user=request.user, movie=movie
            )
            item.delete()
            return Response(
                {"detail": "Removed from watchlist"},
                status=status.HTTP_204_NO_CONTENT
            )


# @extend_schema(
#     summary="Movie detail",
#     description="Retrieve full details for one movie (by slug).",
#     responses={200: MovieDetailSerializer},
#     tags=["Movies"],
# )
# class MovieDetailView(generics.RetrieveAPIView):
#     """
#     Movie full detail, including:
#     - genres
#     - comments
#     - whether it’s in the current user’s watchlist
#     """
#     queryset = Movie.objects.prefetch_related('genres', 'comments__user', 'watchlisted_by')
#     serializer_class = MovieDetailSerializer
#     lookup_field = 'slug'
#     permission_classes = [permissions.AllowAny]


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
    tags=["Watchlist"],
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
        "id": serializers.IntegerField(),
        "title": serializers.CharField(),
        "predicted_score": serializers.FloatField(),
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
    Update its score (0.0 - 5.0).

    delete:
    Delete the rating.
    """
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Prevent access to other users' ratings
        return Rating.objects.filter(user=self.request.user)