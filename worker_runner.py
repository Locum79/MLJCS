import redis
from rq import Worker, Queue
from rq.timeouts import JobTimeoutException
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
    worker.work(with_scheduler=True)  # enables enqueue_in / scheduled jobs
