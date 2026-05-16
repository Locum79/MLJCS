import time
import logging
from app import create_app, db
from app.models import JobQueue
from app.registry.tasks import get_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('worker_loop')

POLL_INTERVAL = 3  # seconds

def run_worker():
    app = create_app()
    logger.info("Starting background worker loop...")
    with app.app_context():
        while True:
            job = (
                JobQueue.query
                .filter_by(status="pending")
                .order_by(JobQueue.created_at.asc())
                .first()
            )

            if not job:
                time.sleep(POLL_INTERVAL)
                continue

            try:
                job.status = "running"
                job.attempts += 1
                db.session.commit()

                logger.info(f"Executing job {job.id} ({job.task_name})...")
                task_fn = get_task(job.task_name)
                task_fn(**(job.payload or {}))

                job.status = "done"
                db.session.commit()
                logger.info(f"Job {job.id} completed successfully.")

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}", exc_info=True)
                job.status = "failed"
                db.session.commit()

            time.sleep(1)

if __name__ == "__main__":
    run_worker()
