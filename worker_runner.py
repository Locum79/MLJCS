import redis
from rq import Worker, Queue, Connection
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
redis_conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(Queue('certificates'))
        worker.work()
