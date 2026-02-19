import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.vercel')

sys.path.insert(0, os.path.dirname(__file__))

# Run migrations on startup (for serverless environments)
if os.environ.get('VERCEL_ENV'):
    try:
        import django
        django.setup()
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb', verbosity=0)
    except Exception as e:
        print(f"Migration warning: {e}")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
