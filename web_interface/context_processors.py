from django.conf import settings


def env_variables(request):
    """
    Return APPLICATION_BUILD_REVISION environment variable along context variables.
    """
    return {
        'APPLICATION_BUILD_REVISION': settings.APPLICATION_BUILD_REVISION,
    }
