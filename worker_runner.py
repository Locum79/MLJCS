import redis
from rq import Worker, Queue
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
redis_conn = redis.from_url(redis_url)

if __name__ == '__main__':
    queues = [Queue('certificates', connection=redis_conn)]
    worker = Worker(queues, connection=redis_conn)
    try:
        worker.work(with_scheduler=True)
    except TypeError:
        # Older rq version without with_scheduler param
        worker.work()
