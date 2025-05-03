import logging

from django.conf import settings
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from .tasks import send_password_reset_email

logger = logging.getLogger(__name__)


@receiver(reset_password_token_created)
def password_reset_token_created_handler(sender, reset_password_token, *args, **kwargs):
    """
    Handles password-reset-token creation by queueing an email via Celery.
    """
    user = reset_password_token.user

    # 1) Build the URL the frontend will use
    frontend_base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    if not frontend_base:
        logger.error("FRONTEND_URL is not set in settings; cannot build reset link.")
        return

    reset_url = f"{frontend_base}/reset-password?token={reset_password_token.key}"
    logger.debug(f"Password reset URL for {user.email}: {reset_url}")

    # 2) Queue the email task
    try:
        send_password_reset_email.delay(
            user_id=user.id,
            subject="Password Reset Request",
            email_template="accounts/password_reset_email.html",
            context={
                "user_name": user.get_full_name(),
                "reset_url": reset_url,
            },
        )
        logger.info(f"Queued password-reset email to {user.email}")
    except Exception as e:
        logger.exception(f"Failed to queue password-reset email for {user.email}: {e}")
