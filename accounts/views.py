import logging
from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from django_rest_passwordreset.views import ResetPasswordRequestToken, ResetPasswordConfirm
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, inline_serializer
)

from .serializers import (
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer,
    UserSerializer,
)
from .tasks import send_password_change_email

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(
    summary="Register a new user",
    description="Creates a new account.  ",
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(
            response=UserSerializer,
            description="User created successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    summary="Created User",
                    value={
                        "id": 17,
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "email": "jane.smith@example.com",
                        "gender": "female",
                        "preferred_genres": [1, 4],
                        "date_joined": "2025-05-01T12:34:56Z",
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=["Authentication"],
)
class UserRegistrationView(generics.CreateAPIView):
    """
    POST /api/register/
    Creates a new user.
    """
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()


@extend_schema(
    summary="Obtain JWT tokens",
    description="Given valid `email` and `password`, returns a pair of JWT tokens.",
    request=inline_serializer(
        name="TokenObtainRequest",
        fields={
            "email": serializers.EmailField(),
            "password": serializers.CharField(style={'input_type': 'password'}),
        },
    ),
    responses={
        200: inline_serializer(
            name="TokenObtainResponse",
            fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
            }
        ),
        401: OpenApiResponse(description="Invalid credentials"),
    },
    tags=["Authentication"],
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/token/
    Returns JWT refresh & access tokens.
    """
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    summary="Refresh JWT tokens",
    description="Refresh JWT access tokens using a valid refresh token.",
    responses={
        200: OpenApiResponse(description="Tokens refreshed successfully"),
        401: OpenApiResponse(description="Unauthorized - Invalid refresh token")
    },
    tags=["Authentication"],
)   
class CustomTokenRefreshView(TokenRefreshView):
    pass 
    

@extend_schema(
    summary="Verify JWT token",
    description="Verify the validity of a JWT access token.",
    responses={
        200: OpenApiResponse(description="Token is valid"),
        401: OpenApiResponse(description="Unauthorized - Invalid token")
    },
    tags=["Authentication"],
)
class CustomTokenVerifyView(TokenVerifyView,):
    pass



@extend_schema(
    summary="Request password reset",
    description="Send a password reset email (if the address exists).",
    request=inline_serializer(
        name="PasswordResetRequest",
        fields={"email": serializers.EmailField()},
    ),
    responses={
        200: OpenApiResponse(description="If that email exists, a reset link has been sent."),
    },
    tags=["Authentication"],
)
class CustomPasswordResetRequestView(ResetPasswordRequestToken):
    """
    POST /api/password-reset/
    """
    throttle_classes = []  # you can add throttles here

    def get_user_by_email(self, email):
        email = email.strip()
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("No account found with that email address.")
            )


@extend_schema(
    summary="Confirm password reset",
    description="Given a valid reset token and a new password, updates the user's password.",
    request=inline_serializer(
        name="PasswordResetConfirm",
        fields={
            "token": serializers.CharField(),
            "password": serializers.CharField(style={'input_type': 'password'}),
        },
    ),
    responses={
        200: OpenApiResponse(description="Password has been reset successfully."),
        400: OpenApiResponse(description="Invalid token or password."),
    },
    tags=["Authentication"],
)
class CustomPasswordResetConfirmView(ResetPasswordConfirm):
    """
    POST /api/password-reset/confirm/
    """


@extend_schema(
    summary="Change current user's password",
    description="Authenticated users can change their own password by providing the old and new passwords.",
    request=PasswordChangeSerializer,
    responses={
        200: OpenApiResponse(
            description="Password changed",
            examples=[OpenApiExample("Success", summary="Changed", value={"detail": "Your password has been changed successfully."})]
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=["Profile"],
)
class PasswordChangeView(generics.UpdateAPIView):
    """
    POST /api/password-change/
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # notify via email asynchronously
        send_password_change_email(user.id)
        return Response(
            {"detail": _("Your password has been changed successfully.")},
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve current user's profile",
        description="Fetch the profile details of the currently authenticated user.",
        responses={200: UserSerializer},
        tags=["Profile"],
    ),
    patch=extend_schema(
        summary="Update current user's profile",
        description=(
            "Partially update the authenticated user's profile fields. "
            "Only non-sensitive fields (e.g. first_name, last_name, gender, preferred_genres) "
            "may be modified. Email changes must be unique."
        ),
        request=UserSerializer,
        responses={200: UserSerializer},
        tags=["Profile"],
    ),
    delete=extend_schema(
        summary="Delete current user's account",
        description="Permanently delete the authenticated user's account. This action cannot be undone.",
        responses={204: OpenApiResponse(description="User account deleted successfully.")},
        tags=["Profile"],
    ),
)
class UserDetailsView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/user/    → Retrieve your own profile.
    PATCH /api/user/  → Update allowed fields on your profile.
    DELETE /api/user/ → Delete your account.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Always operate on the currently authenticated user
        return self.request.user

    def delete(self, request, *args, **kwargs):
        # Perform deletion and return 204
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="List all users",
    responses={200: UserSerializer(many=True)},
    tags=["User Management"],
)
class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(
    summary="Total user count",
    responses={
        200: inline_serializer(
            name="UserCountResponse",
            fields={"total": serializers.IntegerField()},
        )
    },
    tags=["User Management"],
)
class TotalUserCountView(APIView):
    """
    GET /api/users/count/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"total": User.objects.count()})
