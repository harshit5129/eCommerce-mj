import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gevent'
worker_connections = 1000
threads = int(os.getenv('GUNICORN_THREADS', '4'))

timeout = 120
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 100

preload_app = True

accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

capture_output = True

forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'https',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on',
}

def on_starting(server):
    server.log.info("Starting Gunicorn server...")

def when_ready(server):
    server.log.info(f"Server is ready. Workers: {workers}, Threads: {threads}")

def on_exit(server):
    server.log.info("Server is shutting down...")

def pre_fork(server, worker):
    pass

def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def worker_int(worker):
    worker.log.info(f"Worker received INT or QUIT signal (pid: {worker.pid})")

def worker_abort(worker):
    worker.log.info(f"Worker received SIGABRT signal (pid: {worker.pid})")
