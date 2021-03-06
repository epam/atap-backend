"""
Django settings for web_interface project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import uuid
from datetime import timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

CURRENT_ENV = os.getenv('CURRENT_ENV', 'local')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = CURRENT_ENV != 'PROD'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(uuid.uuid4()) if CURRENT_ENV == 'PROD' else 'dvt%$^#&5hk#%h573j,h3%^H65hkg%$g3^'

APPLICATION_BUILD_REVISION = os.getenv('APPLICATION_BUILD_REVISION')
ALLOWED_HOSTS = ['*']

CORS_ALLOWED_ORIGINS = [
    'http://10.244.219.90',   # dev
    'http://10.244.221.170',  # staging
    'http://10.244.217.158',  # prod
    'http://10.244.219.53',   # dima
    'http://localhost:3000',
    'http://localhost:8080',
    'http://localhost',
    'http://localhost:8000',
    'http://127.0.0.1:8083',
    'http://127.0.0.1',
    'http://ecsa00401332.epam.com:8000',
    'http://ecsa00401332.epam.com',
    'http://10.244.219.139',
]

cors_extra_allowed_origin = os.getenv("CORS_EXTRA_ALLOWED_ORIGIN", None)
if cors_extra_allowed_origin:
    CORS_ALLOWED_ORIGINS.append(cors_extra_allowed_origin)

https_origins = [origin.replace("http", "https") for origin in CORS_ALLOWED_ORIGINS]

CORS_ALLOWED_ORIGINS.extend(https_origins)

# TODO revise after deployment to PROD (becomes unused after token authentication)
CORS_ALLOW_CREDENTIALS = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_celery_results',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_api_key',
    'django.contrib.staticfiles',
    'drf_yasg',
    'django_filters',
    'corsheaders',
    'axes',
    'web_interface.apps.activity',
    'web_interface.apps.api_key',
    'web_interface.apps.auth_user',
    'web_interface.apps.page',
    'web_interface.apps.project',
    'web_interface.apps.job',
    'web_interface.apps.framework_data',
    'web_interface.apps.issue',
    'web_interface.apps.report',
    'web_interface.apps.task',
    'web_interface.apps.task_planner',
    'web_interface.apps.jira',
    'web_interface.apps.system',
]

AUTH_USER_MODEL = 'auth_user.AuthUser'
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
AXES_LOCK_OUT_AT_FAILURE = False
AXES_COOLOFF_TIME = timedelta(minutes=5)

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'web_interface.api.authentication.ExpiringTokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'web_interface.api.pagination.PageNumberPaginationExtended',
    'PAGE_SIZE': 20
}

# temporary disabled for development productivity
# API_TOKEN_EXPIRE_TIME = timedelta(days=1)
API_TOKEN_EXPIRE_TIME = None

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'web_interface.middle.DisableCSRFMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'web_interface.urls'

if 'USE_DOCKER' in os.environ:
    CELERY_BROKER_URL = 'amqp://rabbitmq'
    CELERY_RESULT_BACKEND = 'rpc://rabbitmq'
else:
    CELERY_BROKER_URL = 'amqp://localhost'
    CELERY_RESULT_BACKEND = 'rpc://localhost'

CELERY_ROUTES = {
    'web_backend.tasks.test_page': {'queue': 'longlived'},
    'web_backend.tasks.sitemap': {'queue': 'shortlived'},
    'web_backend.tasks.receive_rabbitmq_messages': {'queue': 'rabbitmq_receiver'},
    'web_backend.tasks.verify_tasks_running': {'queue': 'shortlived'},
}

CELERY_BEAT_SCHEDULE = {
    "receive_rabbitmq_periodically": {
        'task': 'web_interface.apps.task.tasks.receive_rabbitmq_messages',
        'schedule': 10.0,
        'options': {
            'queue': 'rabbitmq_receiver'
        }
    },
    "verify_tasks_running_periodically": {
        'task': 'web_interface.apps.task.tasks.verify_tasks_running',
        'schedule': 30.0,
        'options': {
            'queue': 'shortlived'
        }
    },
    "check_for_planned_tasks": {
        'task': 'web_interface.apps.task.tasks.check_for_planned_tasks',
        'schedule': 60.0,
        'options': {
            'queue': 'shortlived'
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'web_interface', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'web_interface.context_processors.env_variables',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_interface.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

if 'USE_DOCKER' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'web_interface',
            'USER': 'web_interface_user',
            'PASSWORD': 'postgres',
            'HOST': 'db',
            'PORT': '',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'web_interface',
            'USER': 'web_interface_user',
            'PASSWORD': 'postgres',
            'HOST': '127.0.0.1',
            'PORT': '',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('WEB_INTERFACE_MEDIA_ROOT', './media')
STATIC_ROOT = os.getenv('WEB_INTERFACE_STATIC_ROOT', './static')

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = ''
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': True,
#     'filters': {
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue',
#         }
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#         }
#     },
#     'loggers': {
#         'django.db.backends': {
#             'level': 'DEBUG',
#             'handlers': ['console'],
#             'propagate': False
#         }
#     }
# }
