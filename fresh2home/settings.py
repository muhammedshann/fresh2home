"""
Django settings for fresh2home project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("Missing SECRET_KEY in .env file")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "admin_side",
    "user_side",
    'django.contrib.sites',  # Required for allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'corsheaders',#razorpay
]

SOCIALACCOUNT_PROVIDERS = {
    "google":{
        "SCOPE":[
            "profile",
            "email"
        ],
        "AUTH_PARAMS":{"access_type":"online"}
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    # razorpay
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000", 
    "http://127.0.0.1:3000",
]

ROOT_URLCONF = 'fresh2home.urls'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Global template directory
        'APP_DIRS': True,  # Automatically load templates from app/templates/
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fresh2home.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
# STATICFILES_DIRS = [
#     BASE_DIR / "admin_side/static",  # Static directory for admin_side
#     # BASE_DIR / "user_side/static",   # Static directory for user_side
# ]


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#custom
AUTH_USER_MODEL = 'user_side.User'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # Default
    'allauth.account.auth_backends.AuthenticationBackend',  # Allauth
)

# LOGIN_REDIRECT_URL = 'homepage'  # Redirect to home after successful login
# LOGOUT_REDIRECT_URL = 'signin'  # Redirect to home after successful login
# ACCOUNT_SIGNUP_REDIRECT_URL = 'homepage'

ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_EMAIL_VERIFICATION = "optional"  # or "mandatory"
# LOGIN_REDIRECT_URL = '/'  # Redirect URL after login

RAZORPAY_KEY_ID = 'rzp_test_g3S5TtMqklMDK2'
RAZORPAY_KEY_SECRET = '5BjQf1ItYKlVfwzHHCRe6uQQ'
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

# Add site ID for allauth
SITE_ID = 2

# Authentication settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = True

# Google OAuth settings
SOCIAL_AUTH_GOOGLE_CLIENT_ID = os.getenv("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
SOCIAL_AUTH_GOOGLE_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_SECRET")

# Redirect URLs
LOGIN_REDIRECT_URL = '/'  # Redirect after successful login
LOGOUT_REDIRECT_URL = '/'  # Redirect after logout

SOCIALACCOUNT_LOGIN_ON_GET = True  # Redirect users directly to Google login

# reset password

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Use console for testing
# DEFAULT_FROM_EMAIL = 'muhammedshan930o@gmail.com@example.com'

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'fresh2homee@gmail.com'  # your Gmail address
# EMAIL_HOST_PASSWORD = 'zbal foru uwns otqp'  # use the app password, not the regular password
# DEFAULT_FROM_EMAIL = 'fresh2homee@gmail.com'  # this can be the same email as EMAIL_HOST_USER

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'fresh2homee@gmail.com'
EMAIL_HOST_PASSWORD = 'fynadhnmtmayzsri'  # Use the app password you generated

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',  # Gray
    messages.INFO: 'info',  # Blue
    messages.SUCCESS: 'success',  # Green
    messages.WARNING: 'warning',  # Yellow
    messages.ERROR: 'danger',  # Red
}





