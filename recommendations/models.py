from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, F
from decimal import Decimal
from django.core.cache import cache

User = get_user_model()


class Genre(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Enter a unique name for the genre."),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        help_text=_("URL-safe identifier generated from the name."),
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"], name="genre_slug_idx"),
        ]

    def save(self, *args, **kwargs):
        # Always keep slug in sync with name
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Movie(models.Model):
    movielens_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("MovieLens identifier for the movie."),
    )
    imdb_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("IMDB identifier for the movie."),
    )
    tmdb_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("TMDB identifier for the movie."),
    )
    title = models.CharField(
        max_length=255,
        help_text=_("The title of the movie."),
    )
    overview = models.TextField(
        blank=True,
        help_text=_("Brief description of the movie."),
    )
    release_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("The release date of the movie."),
    )
    cast = models.JSONField(
        blank=True,
        null=True,
        help_text=_("List of main cast members as JSON array."),
    )
    language = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("The primary language of the movie."),
    )
    poster_url = models.URLField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_("URL to the movie's poster image."),
    )
    trailer_url = models.URLField(
        blank=True,
        null=True,
        help_text=_("URL to the movie's trailer."),
    )
    genres = models.ManyToManyField(
        Genre,
        related_name="movies",
        help_text=_("Genres associated with this movie."),
    )
    average_rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        db_index=True,
        help_text=_("Calculated average rating based on user reviews."),
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text=_("URL-safe identifier generated from the title."),
    )

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["movielens_id"], name="movie_ml_id_idx"),
            models.Index(fields=["slug"], name="movie_slug_idx"),
        ]

    def save(self, *args, **kwargs):
        # 1) Generate the “base” slug from title
        base_slug = slugify(self.title)

        # 2) If this is a new object, or the title changed, we need to (re)generate slug
        if not self.slug or self.slug != base_slug:
            slug = base_slug
            counter = 1

            # 3) Loop until we find a slug that isn’t taken by another movie
            while Movie.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def update_average_rating(self):
        """
        Recalculate and persist the average rating only if it has changed.
        """
        agg = self.ratings.aggregate(avg=Avg('score'))['avg'] or Decimal('0.00')
        # ensure agg is a Decimal to match the field type
        if not isinstance(agg, Decimal):
            agg = Decimal(str(agg))
        if self.average_rating != agg:
            self.average_rating = agg
            # only update that one column
            self.save(update_fields=['average_rating'])

    def __str__(self):
        # Show title plus year, for readability
        year = self.release_date.year if self.release_date else "n.d."
        return f"{self.title} ({year})"



class Comment(models.Model):
    user = models.ForeignKey(
        User, related_name="comments", on_delete=models.CASCADE
    )
    movie = models.ForeignKey(
        Movie, related_name="comments", on_delete=models.CASCADE
    )
    comment = models.TextField(help_text=_("User's comment about the movie."))
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["movie", "timestamp"], name="comment_movie_time_idx"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} on {self.movie.title}"


class Watchlist(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watchlist"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="watchlisted_by"
    )
    watched = models.BooleanField(
        default=False, help_text=_("Whether the user has watched the movie.")
    )
    added_on = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = [("user", "movie")]
        ordering = ["-added_on"]
        indexes = [
            models.Index(fields=["user", "watched"], name="watchlist_user_watched_idx"),
        ]

    def __str__(self):
        status = "✓" if self.watched else "⏳"
        return f"{status} {self.user.get_full_name()} – {self.movie.title}"


class Rating(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="ratings"
    )
    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        help_text=_("User's rating for the movie (0.0–5.0)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "movie")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["movie", "score"], name="rating_movie_score_idx"),
        ]

    def __str__(self):
        return f"{self.score:.1f} by {self.user.get_short_name()} on {self.movie.title}"
