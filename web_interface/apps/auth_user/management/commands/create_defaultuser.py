from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates an admin user non-interactively if it does not exist'

    def handle(self, *args, **options):
        AuthUser = get_user_model()
        if not AuthUser.objects.filter(username='admin').exists():
            AuthUser.objects.create_superuser(username='admin',
                                              email='admin@example.com',
                                              password='admin')
