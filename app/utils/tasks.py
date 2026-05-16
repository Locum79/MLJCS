import logging
import threading
from flask import current_app
logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.task_queue = self
        logger.info('TaskQueue initialized (Mode: Threading)')

    def enqueue(self, func_path, **kwargs):
        logger.info(f'Enqueuing task: {func_path} with args: {list(kwargs.keys())}')

        def run_task(app_context, f_path, f_kwargs):
            try:
                import importlib
                module_path, func_name = f_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
                with app_context:
                    func(**f_kwargs)
            except Exception as e:
                logger.error(f'Task {f_path} failed: {e}', exc_info=True)
        thread = threading.Thread(target=run_task, args=(current_app.app_context(), func_path, kwargs), daemon=True)
        thread.start()
        return True


task_queue = TaskQueue()
