from pathlib import Path
from ai import constants

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-dhc8#z+$%rxt7cu+fsk1^@n1__!%sfwbww_&_+#=#+83^hv0#g'


DEBUG = False

ALLOWED_HOSTS = [
    "aravindpillai.com", "ai-be.aravindpillai.com", 
    "localhost", "127.0.0.1"
]

CORS_ALLOWED_ORIGINS = [
    "https://aravindpillai.com", "https://www.aravindpillai.com", 
    "https://www.ai-be.aravindpillai.com", "https://ai-be.aravindpillai.com",
    "http://localhost:8080", "http://127.0.0.1:8080"
]


INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cv',
    'claims'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
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

WSGI_APPLICATION = 'ai.wsgi.application'

SQLLITE = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
}

POSTGRES = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": constants.DB_NAME,
    "USER": constants.DB_USERNAME,
    "PASSWORD": constants.DB_PASSWORD,
    "HOST": constants.DB_HOST,
    "PORT": constants.DB_PORT,
    "CONN_MAX_AGE": 60,
    "OPTIONS": {"sslmode": "require"}
}

DATABASES = {
    'default': SQLLITE if DEBUG else POSTGRES
}


AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' },
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / STATIC_URL
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'