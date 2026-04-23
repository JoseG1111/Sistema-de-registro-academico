"""Configuracion base de Gunicorn para Ubuntu."""

from __future__ import annotations

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(
    os.getenv(
        "WEB_CONCURRENCY",
        str(max(2, min(multiprocessing.cpu_count() * 2 + 1, 8))),
    )
)
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 30
worker_class = "gthread"
accesslog = "-"
errorlog = "-"
capture_output = True
