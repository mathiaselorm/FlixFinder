"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 5.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

import os
import environ
from pathlib import Path
from datetime import timedelta
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Initialise environment variables
env = environ.Env()
#Locates the .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=False)


ALLOWED_HOSTS = ['*']

TMDB_API_KEY = env('TMDB_API_KEY')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'django_rest_passwordreset',
    'corsheaders',
    'drf_spectacular',
    'accounts.apps.AccountsConfig',
    'recommendations.apps.RecommendationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FlixFinder API',
    'DESCRIPTION': 'API Documentation for FlixFinder',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

DJANGO_REST_PASSWORDRESET_TOKEN_CONFIG = {
    'CLASS': 'django_rest_passwordreset.tokens.RandomStringTokenGenerator',
    'OPTIONS': {
        'lifetime': timedelta(hours=1)
    }
}

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# LOGGING = {
#             'version': 1,
#             'disable_existing_loggers': False,
#             'formatters': {
#                 'verbose': {
#                     'format': '{levelname} {asctime} {module} {message}',
#                     'style': '{',
#                 },
#             },
#             'handlers': {
#                 'file': {
#                     'level': 'ERROR',
#                     'class': 'logging.handlers.RotatingFileHandler',
#                     'filename': 'django_errors.log',
#                     'formatter': 'verbose',
#                 },
#             },
#             'loggers': {
#                 'django': {
#                     'handlers': ['file'],
#                     'level': 'DEBUG',
#                     'propagate': True,
#                 },
#                 'accounts': {
#                     'handlers': ['file'],
#                     'level': 'INFO',
#                     'propagate': True,
#                 },
#                 'recommendations': {
#                     'handlers': ['file'],
#                     'level': 'INFO',
#                     'propagate': True,
#                 },	
#             },
#         }


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': env.db()
}



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'

EMAIL_BACKEND = 'accounts.utils.BrevoAPIBackend'

FRONTEND_URL = 'http://127.0.0.1:8000'  # Replace with your frontend URL

# Email API configuration
BREVO_API_KEY = env('BREVO_API_KEY')
BREVO_DOMAIN = env('BREVO_DOMAIN')

# Default email settings
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='memis@melarc.me')

broker_connection_retry_on_startup = True

# Celery configuration
CELERY_BROKER_URL = "redis://127.0.0.1:6380/0"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6380/0"


CELERY_TASK_EAGER_PROPAGATES = True  # Raise errors immediately
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ALWAYS_EAGER = False  # Set to True only for local development if needed

BROKER_TRANSPORT_OPTIONS = {
    "max_connections": 2,
    "socket_keepalive": True,     
    "retry_on_timeout": True, 
}

# Logging for Celery workers
CELERY_WORKER_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
CELERY_WORKER_TASK_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(task_name)s[%(task_id)s]: %(message)s"
CELERY_WORKER_REDIRECT_STDOUTS = True
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = 'DEBUG'


PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour in seconds

CORS_ALLOW_ALL_ORIGINS = True

# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "https://flixfinder-pwa.vercel.app"
# ]

CORS_ALLOW_CREDENTIALS = True



CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-csrf-token',
]

if DEBUG:
    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = False
else:
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True

CSRF_COOKIE_HTTPONLY = False  # Allows JavaScript to access the token
CSRF_COOKIE_NAME = "csrftoken"  # Name of the CSRF token in cookies
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "https://flixfinder-pwa.vercel.app",
]  


# Password reset token expiration time in hours
DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME = 1 # Default is 24 hours
# Prevent information leakage for non-existent users on password reset request
DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE = False  # Default is False
# Allow password reset for users without a usable password
DJANGO_REST_MULTITOKENAUTH_REQUIRE_USABLE_PASSWORD = True  # Default is True
