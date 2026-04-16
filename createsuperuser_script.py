import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nyazeekwet.settings')
django.setup()

User = get_user_model()
username = 'admin'
email = 'admin@example.com'
password = 'n&L8#vK2zP!mQ5*X'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser "{username}" createed successfully!')
else:
    print(f'Superuser "{username}" already exists.')