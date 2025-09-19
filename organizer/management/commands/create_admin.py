from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create the default admin user'

    def handle(self, *args, **options):
        username = 'Steli'
        email = 'steli.fileva@gmail.com'
        password = 'Parola123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User {username} already exists')
            )
            return
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='admin'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {username}')
        )
