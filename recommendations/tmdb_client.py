import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class TMDbClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.themoviedb.org/3'

    def make_request(self, url, params):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def get_genres(self):
        """Fetch genres from TMDb."""
        url = f"{self.base_url}/genre/movie/list"
        params = {'api_key': self.api_key, 'language': 'en-US'}
        return self.make_request(url, params)

    def get_movies(self, page=1):
        """Fetch movies from TMDb."""
        url = f"{self.base_url}/movie/popular"
        params = {'api_key': self.api_key, 'language': 'en-US', 'page': page}
        return self.make_request(url, params)

    def get_movie_by_imdb_id(self, imdb_id):
        """Fetch TMDB movie ID using IMDb ID."""
        url = f"{self.base_url}/find/{imdb_id}"
        params = {
            'api_key': self.api_key,
            'external_source': 'imdb_id',
            'language': 'en-US'
        }
        return self.make_request(url, params)

    def get_movie_videos(self, movie_id):
        """Fetch videos for a specific movie."""
        url = f"{self.base_url}/movie/{movie_id}/videos"
        params = {'api_key': self.api_key, 'language': 'en-US'}
        return self.make_request(url, params)

    def get_movie_cast(self, movie_id):
        """Fetch cast details for a specific movie from TMDb."""
        url = f"{self.base_url}/movie/{movie_id}/credits"
        params = {'api_key': self.api_key, 'language': 'en-US'}
        return self.make_request(url, params)

    def get_movie_images_by_tmdb_id(self, tmdb_id):
        """
        Fetches images for a movie by TMDB ID.
        """
        url = f"{self.base_url}/movie/{tmdb_id}/images"
        params = {'api_key': self.api_key}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None


    def get_movie_details_by_tmdb_id(self, movie_id):
        """Fetch details for a specific movie from TMDb by its TMDb ID."""
        url = f"{self.base_url}/movie/{movie_id}"
        params = {'api_key': self.api_key, 'language': 'en-US'}
        return self.make_request(url, params)
