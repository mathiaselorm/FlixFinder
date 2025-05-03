# recommendations/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('genres/', views.GenresView.as_view(), name='home'),
    path('genres/<slug:slug>/', views.GenreDetailView.as_view(), name='genre-detail'),
    path('movies/<slug:slug>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('watchlist/', views.WatchlistView.as_view(), name='watchlist'),
    path('recommendations/', views.RecommendMoviesView.as_view(), name='recommendations'),
    path('ratings/', views.RatingListCreateView.as_view(), name='rating-list-create'),
    path('ratings/<int:pk>/', views.RatingDetailView.as_view(), name='rating-detail'),
]
