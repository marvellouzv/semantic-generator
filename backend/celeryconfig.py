"""
Celery Worker Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Broker and Backend
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Task configuration
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Performance
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Timeouts
task_soft_time_limit = 25 * 60  # 25 minutes
task_time_limit = 30 * 60  # 30 minutes

# Result storage
result_expires = 86400  # 24 hours

# Logging
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'
