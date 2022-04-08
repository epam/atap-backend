import sentry_sdk
from django.conf import settings
from sentry_sdk.integrations.django import DjangoIntegration

from web_interface.apps.system.models import CheckerParameter


DEFAULT_PARAMETER_VALUES = {
    "VAULT_URL": "http://vault:8200",
    "VAULT_NAMESPACE": "bss-dev/epm-acc",
    "SENTRY_DSN": 'http://9b12af32a2834f958afd1a076db60202@host.docker.internal:9000/1'
}


def get_parameter(key, default_value=None):
    if key in DEFAULT_PARAMETER_VALUES:
        default_value = DEFAULT_PARAMETER_VALUES[key]
    try:
        return CheckerParameter.objects.get(key=key).value
    except CheckerParameter.DoesNotExist:
        CheckerParameter.objects.create(key=key, value=default_value)
        return default_value


SENTRY_DSN = 'http://9b12af32a2834f958afd1a076db60202@host.docker.internal:9000/1'

sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=settings.CURRENT_ENV,
    release=settings.APPLICATION_BUILD_REVISION,
    integrations=[DjangoIntegration()]
)
