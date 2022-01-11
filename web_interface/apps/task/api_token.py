import secrets

from web_interface.apps.api_key.models import CheckerAPIKey
from web_interface.apps.task import models

TOKEN_LENGTH = 20
HASH_LENGTH = 16
PREFIX_LENGTH = 5


def create_token(user, project):
    return CheckerAPIKey.objects.create_key(project=project, user=user, name=project.name)[1]


def create_worker_key(task):
    while True:
        token = secrets.token_hex(TOKEN_LENGTH)
        if not models.WorkerKey.objects.filter(key=token).exists():
            models.WorkerKey.objects.create(task=task, key=token)
            break
    return token


def check_worker_key(key, task):
    return models.WorkerKey.objects.filter(task=task, key=key).exists()


def delete_worker_key(key):
    models.WorkerKey.objects.filter(key=key).delete()


def list_tokens(user):
    tokens = list()
    for token in CheckerAPIKey.objects.filter(user=user):
        tokens.append({
            "id": token.id,
            "project": token.project.name,
            "prefix": "****"
        })
    return tokens


def delete_token(token_id, user):
    try:
        CheckerAPIKey.objects.get(id=token_id, user=user).delete()
        return True
    except CheckerAPIKey.DoesNotExist:
        return False
