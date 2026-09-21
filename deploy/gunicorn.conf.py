# Gunicorn configuration for Faith-n-Action (production).
# Workers: (2 x CPU) + 1 is the standard starting point; the app is
# SQLite-bound in dev-parity mode, so keep workers modest and let nginx
# absorb concurrency. With PostgreSQL, workers can scale with CPU.

import multiprocessing

bind = "0.0.0.0:8000"
workers = min((multiprocessing.cpu_count() * 2) + 1, 9)
worker_class = "sync"
threads = 1
timeout = 120            # PoW block creation can be slow; do not kill mid-block
graceful_timeout = 30
keepalive = 5
max_requests = 1000      # recycle workers to bound memory growth
max_requests_jitter = 100
accesslog = "-"          # stdout -> container logs
errorlog = "-"
loglevel = "info"
proc_name = "faith-n-action"
