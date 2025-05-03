# recommendations/signals.py

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Rating

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Rating)
@receiver(post_delete, sender=Rating)
def update_movie_average_after_rating_change(sender, instance, **kwargs):
    """
    Whenever a Rating is created, updated, or deleted,
    recalculate its movie's average_rating field.
    """
    try:
        instance.movie.update_average_rating()
        logger.debug(f"Updated average_rating for movie {instance.movie.pk}")
    except Exception as e:
        logger.error(f"Failed to update average for movie {instance.movie.pk}: {e}")
