from django.contrib import admin
from .models import Genre, Movie, Comment, Watchlist, Rating

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['imdb_id', 'tmdb_id', 'title', 'release_date', 'display_genres', 'average_rating']
    list_filter = ['release_date', 'genres__name',]
    search_fields = ['title', 'movielens_id', 'imdb_id', 'tmdb_id']
    filter_horizontal = ['genres']
    readonly_fields = ['average_rating', 'slug']
    ordering = ['-release_date']
    
    def display_genres(self, obj):
        return ", ".join([genre.name for genre in obj.genres.all()])
    display_genres.short_description = 'Genres'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'timestamp']
    search_fields = ['user__email', 'movie__title']
    list_filter = ['timestamp']


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'watched', 'added_on']
    list_filter = ['watched', 'added_on']
    search_fields = ['user__email', 'movie__title']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('movie', 'user', 'score', 'created_at', 'updated_at')
    list_filter = ('movie', 'score',)
    search_fields = ('movie__title', 'user__email',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('movie', 'user', 'score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
