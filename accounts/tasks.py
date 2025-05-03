import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def _send_email(subject, template_name, context, recipient_list):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    email.attach_alternative(html_content, "text/html")

    sent = email.send()
    if sent == 0:
        # no messages sent → force a retry / error
        raise Exception(f"Brevo failed to send to {recipient_list}")

    return sent


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id, subject, email_template, context):
    """
    Celery task: sends a password-reset link email.
    Retries up to 3 times on any exception.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"No such user {user_id}; cannot send reset email.")
        return

    if not user.email:
        logger.error(f"User {user_id} has no email; skipping reset email.")
        return

    try:
        _send_email(subject, email_template, context, [user.email])
        logger.info(f"Password reset email sent to {user.email}.")
    except Exception as exc:
        logger.exception(f"Error sending reset email to {user.email}: {exc}")
        # Retries after delay
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_change_email(self, user_id):
    """
    Celery task: notifies user their password was changed.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"No such user {user_id}; cannot send change notification.")
        return

    if not user.email:
        logger.error(f"User {user_id} has no email; skipping change notification.")
        return

    subject = "Your password has been changed"
    context = {"user_name": user.get_full_name()}

    try:
        _send_email(subject, "accounts/password_change.html", context, [user.email])
        logger.info(f"Password-change notification sent to {user.email}.")
    except Exception as exc:
        logger.exception(f"Error sending change-notif to {user.email}: {exc}")
        raise self.retry(exc=exc)
