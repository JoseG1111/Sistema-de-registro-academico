"""Entrypoint WSGI para Gunicorn u otros servidores compatibles."""

from __future__ import annotations

from app.main import create_app

app = create_app()
application = app
