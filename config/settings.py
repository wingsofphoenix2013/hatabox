import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = ["*"]

# APPS
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "staff.apps.StaffConfig",
    "inventory.apps.InventoryConfig",
    "vendors.apps.VendorsConfig",
    "reference.apps.ReferenceConfig",
    "orders.apps.OrdersConfig",
    "rest_framework",
    "corsheaders",
    "accounts",
]

# MIDDLEWARE
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASE (critical fix)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# LOCALE
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

# STATIC
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# STORAGE (safe for local)
AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
AWS_S3_ENDPOINT_URL = (
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    if R2_ACCOUNT_ID
    else None
)

AWS_S3_REGION_NAME = "auto"
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None

R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "")
AWS_S3_CUSTOM_DOMAIN = (
    R2_PUBLIC_BASE_URL.replace("https://", "").replace("http://", "")
    if R2_PUBLIC_BASE_URL
    else None
)

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "region_name": AWS_S3_REGION_NAME,
            "default_acl": AWS_DEFAULT_ACL,
            "querystring_auth": AWS_QUERYSTRING_AUTH,
            "custom_domain": AWS_S3_CUSTOM_DOMAIN,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://hatabox-frontend.onrender.com",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "https://hatabox-frontend.onrender.com",
]

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True