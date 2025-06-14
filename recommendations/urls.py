# recommendations/urls.py

from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import MovieViewSet

router = DefaultRouter()
router.register(r'movies', MovieViewSet, basename='movie')



urlpatterns = [
    path("", include(router.urls)),
    path('genres/', views.GenresView.as_view(), name='home'),
    path('genres/<slug:slug>/', views.GenreDetailView.as_view(), name='genre-detail'),
    path('movies/search/', views.MovieSearchView.as_view(), name='movie-search'),
    # path('movies/<slug:slug>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('watchlist/', views.WatchlistView.as_view(), name='watchlist'),
    path('recommendations/', views.RecommendMoviesView.as_view(), name='recommendations'),
    path('ratings/', views.RatingListCreateView.as_view(), name='rating-list-create'),
    path('ratings/<int:pk>/', views.RatingDetailView.as_view(), name='rating-detail'),
]
