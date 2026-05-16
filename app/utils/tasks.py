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
        logger.info('TaskQueue initialized (Mode: Threading)')

    def enqueue(self, task_name: str, **kwargs):
        try:
            func = get_task(task_name)
        except KeyError:
            raise RuntimeError(f"TASK NOT REGISTERED: {task_name}")
            
        kwargs.pop('job_timeout', None)
        
        logger.info(f'Enqueuing task: {task_name} with args: {list(kwargs.keys())}')

        def run_task(app_context, f, f_kwargs):
            try:
                with app_context:
                    f(**f_kwargs)
            except Exception as e:
                logger.error(f'Task {task_name} failed: {e}', exc_info=True)
                
        thread = threading.Thread(target=run_task, args=(current_app.app_context(), func, kwargs), daemon=True)
        thread.start()
        return True


task_queue = TaskQueue()
