from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
import logging

from recommendations.models import Genre
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    preferred_genres = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Genre.objects.all(),
        required=False,
        help_text=_("List of genre IDs the user prefers"),
    )

    # watchlist = WatchlistSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name', 'email',
            'gender', 'preferred_genres',
            'date_joined', 'last_login',
            'is_active', 'is_staff', 'updated_at',
            # 'watchlist',
        )
        read_only_fields = (
            'id', 'date_joined', 'last_login',
            'is_active', 'is_staff',
        )
        extra_kwargs = {
            'first_name': {'label': _("First Name")},
            'last_name': {'label': _("Last Name")},
            'email': {'label': _("Email Address")},
        }

    def validate_email(self, value):
        """
        Ensure email is unique (case-insensitive).
        """
        email = value.strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_("This email is already in use."))
        return email

    def update(self, instance, validated_data):
        """
        Update profile fields but never allow direct superuser or staff elevation.
        """
        # Remove any attempt to update protected fields
        for forbidden in ('is_superuser', 'is_staff'):
            validated_data.pop(forbidden, None)

        # Handle preferred_genres M2M
        if 'preferred_genres' in validated_data:
            instance.preferred_genres.set(validated_data.pop('preferred_genres'))

        # Update the rest
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        logger.info(f"User {instance.email} updated fields: {list(validated_data.keys())}")
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Registers a new user, hashing the password and setting preferred_genres.
    """
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label=_("Password"),
    )
    preferred_genres = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Genre.objects.all(),
        required=False,
        help_text=_("List of genre IDs the user prefers"),
    )

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name',
            'email', 'password',
            'gender', 'preferred_genres',
        )

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("This email is already in use."))
        return email

    def validate_password(self, value):
        password_validation.validate_password(value, self.instance or User())
        return value

    def create(self, validated_data):
        genres = validated_data.pop('preferred_genres', [])
        password = validated_data.pop('password')
        # create_user handles set_password + save
        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            first_name=validated_data.get('first_name',''),
            last_name=validated_data.get('last_name',''),
            gender=validated_data.get('gender',''),
        )
        if genres:
            user.preferred_genres.set(genres)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Issue JWTs that carry email and name claims.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email']      = user.email
        token['first_name'] = user.first_name
        token['last_name']  = user.last_name
        return token


class PasswordChangeSerializer(serializers.Serializer):
    """
    Changes a user's password, verifying the old one first.
    """
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label=_("Old Password"),
    )
    new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label=_("New Password"),
    )

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs.get('old_password', '')):
            raise ValidationError({"old_password": _("Old password is incorrect.")})
        password_validation.validate_password(attrs['new_password'], user)
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        logger.info(f"User {user.email} changed their password.")
        return user
