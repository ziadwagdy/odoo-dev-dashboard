from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Ensure admin and developer groups exist'

    def handle(self, *args, **options):
        for name in ('admin', 'manager', 'developer'):
            _, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created group: {name}')
            else:
                self.stdout.write(f'Group already exists: {name}')
