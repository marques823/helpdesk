"""
Django settings for helpdesk project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Obter hosts permitidos do arquivo .env ou usar uma lista padrão
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,10.10.10.2,helpdesk.tecnicolitoral.com,helpdesk.tecnicolitoral.com:8002', cast=Csv())

# Garantir que o host que está causando o erro seja incluído
if 'helpdesk.tecnicolitoral.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('helpdesk.tecnicolitoral.com')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'tickets',
    # 'csp',  # Content Security Policy - comentado temporariamente
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'tickets.middleware.security_middleware.UserFuncionarioMiddleware',
    'tickets.middleware.security_middleware.LoginExemptMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tickets.middleware.security_middleware.SecurityMiddleware',
    # 'csp.middleware.CSPMiddleware',  # Comentado temporariamente
]

ROOT_URLCONF = 'helpdesk_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'helpdesk_app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.sa-east-1.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'AKIRNDURIDBDYRURIWI5'
EMAIL_HOST_PASSWORD jdjdhdhrhdhjfjfjfjfjfhfhf3Lw2'
DEFAULT_FROM_EMAIL = 'suporte@helpdesk.com'
EMAIL_ENABLED = True

# URL do site para uso em links de email
SITE_URL = 'https://helpdesk.helpdesk.com'

# Se o envio de e-mails estiver desativado, usar o backend de console
if not EMAIL_ENABLED:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'tickets:dashboard'
LOGOUT_REDIRECT_URL = 'home'

# URLs que não precisam de autenticação
LOGIN_EXEMPT_URLS = [
    'login',
    'logout',
    'logout-success',
    'home',
]

# Configurações de autenticação
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Configurações de sessão
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True  # Cookies só podem ser acessados através de HTTP, não JavaScript
SESSION_SAVE_EVERY_REQUEST = True  # Atualiza o cookie de sessão a cada requisição

# Configurações de CSRF e segurança
CSRF_TRUSTED_ORIGINS = [
    'helpdesk.helpdesk.com',
    'https://helpdesk.helpdesk.com:8002',
    'http://helpdesk.helpdesk.com:8002',
    'http://helpdesk.helpdesk.com',
    'http://10.10.10.2:8002',
    'http://10.10.10.2:8000',
    'http://localhost:8000'
]

# Detecção automática se estamos em ambiente de produção
IS_PRODUCTION = not DEBUG

# Em produção, usamos configurações mais seguras
if IS_PRODUCTION:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
else:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

CSRF_COOKIE_HTTPONLY = True  # Evita que o token CSRF seja acessível por JavaScript
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'  # Previne clickjacking

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'tickets': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Comentando temporariamente as configurações CSP enquanto resolvemos problemas de inicialização
# CONTENT_SECURITY_POLICY = {
#     'DIRECTIVES': {
#         'default-src': ("'self'",),
#         'style-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "cdnjs.cloudflare.com"),
#         'script-src': ("'self'", "'unsafe-inline'", "'unsafe-eval'", "cdn.jsdelivr.net"),
#         'font-src': ("'self'", "cdn.jsdelivr.net", "cdnjs.cloudflare.com"),
#         'img-src': ("'self'", "data:", "cdn.jsdelivr.net", "cdnjs.cloudflare.com"),
#     }
# }
