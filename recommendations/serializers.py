from rest_framework import serializers
from recommendations.models import Movie, Genre, Comment, Watchlist, Rating



class MovieMiniSerializer(serializers.ModelSerializer):
    in_watchlist = serializers.SerializerMethodField()
    
    class Meta:
        model  = Movie
        fields = [
            "id",
            "slug",          
            "title",
            "poster_url",
            "average_rating",
            "overview",
            "in_watchlist",
        ]
        
    def get_in_watchlist(self, obj):
        user = self.context.get("request").user
        if not user or user.is_anonymous:
            return False
        return obj.watchlisted_by.filter(pk=user.pk).exists()


class GenreWithMoviesSerializer(serializers.ModelSerializer):
    movies = MovieMiniSerializer(
        many=True,
        read_only=True,
        source='movies'     # <-- this is the related_name on your M2M
    )

    class Meta:
        model  = Genre
        fields = ('id', 'name', 'slug', 'movies')
        



class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]


class MovieCardSerializer(serializers.ModelSerializer):
    """
    The minimal “card” you show in a horizontal scroller.
    """
    genres = GenreSerializer(many=True, read_only=True)
    average_rating = serializers.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        model = Movie
        fields = [
            "id",
            "slug",          
            "title",
            "poster_url",
            "average_rating",
            "overview",
            "genres",
        ]


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["user", "comment", "timestamp"]

    def get_user(self, obj):
        return {
            "id":   obj.user.id,
            "name": obj.user.get_full_name(),
            # add avatar_url or email here if you like
        }


class SectionSerializer(serializers.Serializer):
    """
    Generic section: a title + list of MovieCards.
    E.g. {"title":"Top Rated","movies":[ {...}, {...} ]}
    """
    title  = serializers.CharField()
    movies = MovieCardSerializer(many=True)
    

class GenrePageSerializer(serializers.Serializer):
    """
    The data for GET /api/genres/{slug}/
    """
    genre    = serializers.CharField()
    sections = SectionSerializer(many=True)
    

class MovieDetailSerializer(serializers.ModelSerializer):
    """
    The data for GET /api/movies/{slug}/
    """
    genres = GenreSerializer(many=True, read_only=True)
    average_rating = serializers.DecimalField(max_digits=4, decimal_places=2)
    # cast = serializers.ListField(child=serializers.CharField(), source="cast_list")  
    comments = CommentSerializer(many=True)
    in_watchlist = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id", "slug", "title", "overview",
            "release_date", "language",
            "poster_url", "trailer_url", "average_rating",
            "genres", "comments", "in_watchlist"
        ]

    def get_in_watchlist(self, obj):
        user = self.context.get("request").user
        if not user or user.is_anonymous:
            return False
        return obj.watchlisted_by.filter(user=user).exists()


class MovieWatchlistSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        source="movie.title",
        read_only=True,
        help_text="The movie’s title"
    )
    in_watchlist = serializers.SerializerMethodField(
        help_text="Whether the movie is in the user’s watchlist"
    )
    added_on = serializers.DateTimeField(
        read_only=True,
        help_text="When the movie was added to the watchlist",
    )

    class Meta:
        model = Watchlist
        fields = ["title", "in_watchlist", "added_on"]

    def get_in_watchlist(self, obj):
        # Always true for a Watchlist instance
        return True


class WatchlistSerializer(serializers.ModelSerializer):
    """
    The data for GET /api/watchlist/
    [
      {
        "movie": { ...MovieCard fields... },
        "watched": false,
        "added_on": "2025-04-30T12:34:56Z"
      },
      ...
    ]
    """
    movie    = MovieCardSerializer()
    added_on = serializers.DateTimeField()

    class Meta:
        model = Watchlist
        fields = ["movie", "watched", "added_on"]
        
        

class MovieRecommendationSerializer(serializers.ModelSerializer):
    predicted_score = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = ['id', 'title', 'overview', 'poster_url',  "average_rating", "genres", 'predicted_score']
        
        
        
    def get_predicted_score(self, obj):
    # we’ll pass a dict of scores in the context 
        return self.context.get('predicted_scores', {}).get(obj.pk, 0)
     
 
 
class RatingMiniSerializer(serializers.ModelSerializer):
    """
    A minimal serializer for ratings, used in MovieDetailSerializer.
    """
    user = serializers.StringRelatedField(read_only=True)
    movie = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(),
        help_text="ID of the movie being rated"
    )

    class Meta:
        model = Rating
        fields = ['movie', 'user', 'score']
        read_only_fields = ['movie', 'user', 'score'] 
     
class RatingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    movie = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(),
        help_text="ID of the movie being rated"
    )

    class Meta:
        model = Rating
        fields = ['id', 'movie', 'user', 'score', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_score(self, value):
        if not (0.0 <= value <= 5.0):
            raise serializers.ValidationError("The score must be between 0.0 and 5.0.")
        return value

    def create(self, validated_data):
        # Pop the movie, assign current user
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)
