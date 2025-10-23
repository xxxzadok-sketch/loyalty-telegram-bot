import multiprocessing

# Количество worker процессов
workers = multiprocessing.cpu_count() * 2 + 1

# Порт и хост
bind = "0.0.0.0:5000"

# Логирование
accesslog = "-"
errorlog = "-"

# Таймауты
timeout = 60
keepalive = 5