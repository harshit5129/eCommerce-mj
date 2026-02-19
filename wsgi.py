import os
import sys
import subprocess

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.vercel')

sys.path.insert(0, os.path.dirname(__file__))

static_dir = os.path.join(os.path.dirname(__file__), 'staticfiles')
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    try:
        call_command('collectstatic', '--noinput', verbosity=0)
    except Exception:
        pass

application = get_wsgi_application()
