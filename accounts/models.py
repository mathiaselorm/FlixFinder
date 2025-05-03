from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier for authentication.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a Superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class GenderChoices(models.TextChoices):
    MALE = 'male', _('Male')
    FEMALE = 'female', _('Female')
    OTHER = 'other', _('Other')


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_("Required. Enter a valid email address."),
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name  = models.CharField(_('last name'),  max_length=150, blank=True)
    gender     = models.CharField(
        _('gender'),
        max_length=10,
        choices=GenderChoices.choices,
        blank=True,
    )
    preferred_genres = models.ManyToManyField(
        'recommendations.Genre',
        related_name='preferred_users',
        blank=True,
        help_text=_("User's favorite genres for cold-start recommendations."),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_staff    = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active   = models.BooleanField(
        _('active'),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'custom_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email'], name='accounts_email_idx'),
        ]

    def save(self, *args, **kwargs):
        # Normalize the email address
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)
        # Trim whitespace
        self.first_name = self.first_name.strip()
        self.last_name  = self.last_name.strip()
        super().save(*args, **kwargs)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        Falls back to email if both are blank.
        """
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    def get_short_name(self):
        """
        Returns the short name for the user.
        """
        return self.first_name or self.email

    def __str__(self):
        return self.get_full_name()
