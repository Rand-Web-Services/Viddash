import multiprocessing
import os

# Gunicorn config for Viddash
workers = int(os.environ.get("WEB_CONCURRENCY", str(multiprocessing.cpu_count() * 2 + 1)))
threads = int(os.environ.get("GTHREADS", "2"))
worker_class = os.environ.get("WORKER_CLASS", "gthread")  # gthread is fine for IO-bound Flask
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
keepalive = 30
timeout = int(os.environ.get("TIMEOUT", "120"))
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

# Proxy headers (if behind reverse proxy)
forwarded_allow_ips = "*"
proxy_protocol = False
