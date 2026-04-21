import os
import django
from django.contrib.auth import get_user_model
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Shwe_Taike.settings')
django.setup()

load_dotenv()

User = get_user_model()
username = 'admin'
email = 'admin@example.com'
password = os.getenv('admin_password')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser "{username}" createed successfully!')
else:
    print(f'Superuser "{username}" already exists.')