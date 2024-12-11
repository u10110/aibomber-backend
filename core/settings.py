# -*- encoding: utf-8 -*-

import os

import sentry_sdk
from decouple import config
from django.utils.log import DEFAULT_LOGGING
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.django import DjangoIntegration
from unipath import Path

SENTRY_URL = config("SENTRY_URL")
print(f"SENTRY IS {SENTRY_URL}")
if SENTRY_URL:
    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )
else:
    pass

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).parent
print(f"BASE_DIR is {BASE_DIR}")
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="S#perS3crEt_1122")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)
# prod
CSRF_TRUSTED_ORIGINS = ["https://app.eliment.ai", "https://eliment.ai", "https://dev.eliment.ai"]
# load production server from .env
ALLOWED_HOSTS = [
    'eliment.ai',
    'www.eliment.ai',
    "49.13.104.130",
    "dc1-ea-app-01.app.eliment.ai",
    "127.0.0.1",
    "localhost",
    "192.168.122.200",
    "192.168.122.26",
    config("SERVER", default="192.168.122.200"),
]

# Application definition

INSTALLED_APPS = [
    
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "debug_toolbar",
    "django_telegram_login",
    "csp",
    # 'debug_panel',
    "apps.home",
    "apps.authentication",
    "apps.billing",
    "apps.alert",
    "apps.telegram",
    "apps.users_control",
    "import_export",
    "apps.amocrm",
    "django_user_agents",
    "widget_tweaks",
    "apps.templatetags",
    # 'apps.registration'
]
# https://github.com/recamshak/django-debug-panel
# https://github.com/selwin/django-user_agents
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # TODO remove?
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_user_agents.middleware.UserAgentMiddleware",
    # "csp.middleware.CSPMiddleware",
    # 'debug_panel.middleware.DebugPanelMiddleware'
]
# CSRF_COOKIE_SECURE = False

# MIDDLEWARE_CLASSES = (
#     'debug_panel.middleware.DebugPanelMiddleware',
# )

TELEGRAM_BOT_NAME = 'eliment_ai_bot'
TELEGRAM_BOT_TOKEN = '7872283718:AAFlOtPiB1hnMVFlAiq4-nGzpqpuDb80lFQ'
TELEGRAM_LOGIN_REDIRECT_URL = 'https://127.0.0.1:8000'


ROOT_URLCONF = "core.urls"
LOGIN_URL = "login"  # Route defined in home/urls.py
LOGIN_REDIRECT_URL = "login"  # Route defined in home/urls.py
LOGOUT_REDIRECT_URL = "home"  # Route defined in home/urls.py
TEMPLATE_DIR = os.path.join(CORE_DIR, "apps/templates")  # ROOT dir for templates

CSP_FRAME_ANCESTORS = ["'self'", "http://127.0.0.1", "https://telegram.org"]
CSP_DEFAULT_SRC = ["'self'", "https://telegram.org", "https://oauth.telegram.org"]
CSP_SCRIPT_SRC = ["'self'", "https://telegram.org", "https://oauth.telegram.org"]
CSP_STYLE_SRC = ["'self'", "https://telegram.org", "'unsafe-inline'"]
CSP_CONNECT_SRC = ["'self'", "https://telegram.org", "https://oauth.telegram.org"]
CSP_INCLUDE_NONCE_IN = ['script-src']



TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                
                # Добавляем наш контекстный процессор
                'apps.context_processors.balance_processor.user_balance',  # Укажите правильный путь
            ],
        },
    },
]

# WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "sqlite3": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    },
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("PG_NAME", default="postgres"),
        "USER": config("PG_USER", default="postgres"),
        "PASSWORD": config("PG_PASS", default="zAme3GUOkDxl4lT4ZqRo3QjwU"),
        "HOST": config("PG_HOST", default="172.17.0.1"),
        "PORT": config("PG_PORT", default="5432"),
    },
    "OPTIONS": {
        "options": "-c statement_timeout=300000",
    },
}

# DATABASES['default'] = DATABASES['sqlite3']

# DATABASES = {
# 	'default': {
# 		'ENGINE': 'django.db.backends.postgresql_psycopg2',
# 		'NAME': 'postgresql2',
# 		'USER': 'postgres',
# 		'PASSWORD': '555666',
# 		'HOST': 'localhost',
# 		'PORT': '5432',
# 	}
# }

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_L10N = True

USE_TZ = True

#############################################################
# SRC: https://devcenter.heroku.com/articles/django-assets

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)

MEDIA_ROOT = os.path.join(CORE_DIR, "apps/media")
MEDIA_URL = "/media/"

#############################################################
#############################################################
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LANGUAGES = [
    ("ru", _("Russian")),
    ("en", _("English")),
]
LANGUAGES = [("ru", "Russian")]

LOCALE_PATHS = ("/var/www/djangoApp/Billing/object/locale",)
AUTH_USER_MODEL = "authentication.User"
# AUTHENTICATION_BACKENDS = ['apps.authentication.auth_backend.PhoneAuthBackend']
AUTHENTICATION_BACKENDS = (
    "apps.authentication.auth_backend.PhoneAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
)

LOGIN = "Platforma2021"
TEST_MODE = 0
if TEST_MODE:
    PASSWORD1 = "y4l82ue2UfnKBQrdEEM1"
    PASSWORD2 = "lX5gzda39kjRh2WKbp9b"
else:
    PASSWORD1 = "i5ClFCY7cr4Csf9EMR8S"
    PASSWORD2 = "ZA6TAYolgSG2L7ZfzJ26"

DEFAULT_LOGGING["handlers"]["console"]["filters"] = []

# ACCOUNT_ACTIVATION_DAYS = 2 # кол-во дней для хранения кода активации
# AUTH_USER_EMAIL_UNIQUE = True
# EMAIL_HOST = 'localhost'
# EMAIL_PORT = 1025
# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''
# EMAIL_USE_TLS = False
# DEFAULT_FROM_EMAIL = 'info@google.ru'

# ACCOUNT_ACTIVATION_DAYS = 2 # кол-во дней для хранения кода активации
# AUTH_USER_EMAIL_UNIQUE = True
# EMAIL_HOST = ' smtp.yandex.ru'
# EMAIL_PORT = 465
# EMAIL_HOST_USER = 'mail.p@eramp.io'
# EMAIL_HOST_PASSWORD = '#i{YPOM{OV'
# EMAIL_USE_TLS = False
# DEFAULT_FROM_EMAIL = 'mail.p@eramp.io'

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
