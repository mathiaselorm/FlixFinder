from django.urls import path
from . import views
from django_rest_passwordreset.views import (
    ResetPasswordConfirm, 
    ResetPasswordValidateToken,
)




urlpatterns = [
    # User registration endpoint
    path('register/', views.UserRegistrationView.as_view(), name='user-registration'),

    # JWT token obtain endpoint
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/token-refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('login/token-verify/', views.CustomTokenVerifyView.as_view(), name='token_verify'),

    # Password management endpoints
    path('password-reset/request/', views.CustomPasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Endpoint for retrieving, updating, and deleting the authenticated user's account
    path('profile/', views.UserDetailsView.as_view(), name='user-details'),

    # Endpoint to list all users
    path('users/', views.UserListView.as_view(), name='user-list'),

    # Endpoint to get the total number of registered users
    path('users/total/', views.TotalUserCountView.as_view(), name='user-count'),
]
