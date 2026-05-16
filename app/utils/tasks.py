import logging
import threading
from flask import current_app
logger = logging.getLogger(__name__)


from app.registry.tasks import get_task

class TaskQueue:
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.task_queue = self
        logger.info('TaskQueue initialized (Mode: Database-Backed)')

    def enqueue(self, task_name: str, **kwargs):
        # Validate the task exists before queuing
        try:
            get_task(task_name)
        except KeyError:
            raise RuntimeError(f"TASK NOT REGISTERED: {task_name}")
            
        kwargs.pop('job_timeout', None)
        
        logger.info(f'Enqueuing task to DB: {task_name} with args: {list(kwargs.keys())}')

        from app.models import db, JobQueue
        job = JobQueue(
            task_name=task_name,
            payload=kwargs,
            status="pending"
        )
        db.session.add(job)
        db.session.commit()
        return job.id


task_queue = TaskQueue()
