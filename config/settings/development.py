from .base import *  # noqa

DEBUG = True

CORS_ALLOW_ALL_ORIGINS = True

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'api': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
