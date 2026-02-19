import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.vercel')

sys.path.insert(0, os.path.dirname(__file__))

application = get_wsgi_application()
