import multiprocessing

# Configurações do servidor
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
keepalive = 5

# Configurações de logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# Configurações de processo
daemon = False
pidfile = "gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None 