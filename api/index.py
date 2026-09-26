"""Vercel serverless entrypoint: exposes the Django WSGI app as `app`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "linka.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
