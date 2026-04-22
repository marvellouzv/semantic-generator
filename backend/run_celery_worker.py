#!/usr/bin/env python
"""
Celery Worker Launcher
Используйте: python backend/run_celery_worker.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.celery_app import celery_app

if __name__ == '__main__':
    print("🚀 Starting Celery Worker...")
    print("📢 Listening for batch tasks...")
    print("⏹️  Press Ctrl+C to stop\n")
    
    celery_app.worker_main(
        argv=[
            'worker',
            '--loglevel=info',
            '--concurrency=4',  # 4 parallel workers
            '--queues=celery',
            '--broker=' + os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
            '--result-backend=' + os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        ]
    )
