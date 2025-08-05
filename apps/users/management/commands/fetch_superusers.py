from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Fetch and display all superusers'

    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers.exists():
            self.stdout.write(
                self.style.WARNING('No superusers found in the database.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {superusers.count()} superuser(s):')
        )
        
        for user in superusers:
            self.stdout.write(f'ID: {user.id}')
            self.stdout.write(f'Name: {user.name}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Username: {user.username or "N/A"}')
            self.stdout.write(f'Date Joined: {user.date_joined}')
            self.stdout.write(f'Last Login: {user.last_login or "Never"}')
            self.stdout.write(f'Is Active: {user.is_active}')
            self.stdout.write('-' * 40)