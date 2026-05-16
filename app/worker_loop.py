import time
import logging
import uuid
from datetime import datetime, timedelta
from app import create_app, db
from app.models import JobQueue
from app.registry.tasks import get_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('worker_loop')

POLL_INTERVAL = 3  # seconds
STALE_TIMEOUT_MINUTES = 5

def run_worker():
    app = create_app()
    worker_id = str(uuid.uuid4())
    logger.info(f"Starting background worker {worker_id}...")
    with app.app_context():
        while True:
            try:
                stale_time = datetime.utcnow() - timedelta(minutes=STALE_TIMEOUT_MINUTES)
                
                # Atomic claim using SKIP LOCKED
                job = (
                    JobQueue.query
                    .filter(
                        (JobQueue.status == "PENDING") |
                        (JobQueue.status.in_(["CLAIMED", "PROCESSING"]) & (JobQueue.locked_at < stale_time))
                    )
                    .order_by(JobQueue.created_at.asc())
                    .with_for_update(skip_locked=True)
                    .first()
                )

                if not job:
                    db.session.commit()  # Release any locks
                    time.sleep(POLL_INTERVAL)
                    continue

                job.status = "CLAIMED"
                job.locked_at = datetime.utcnow()
                job.locked_by = worker_id
                job.attempts += 1
                db.session.commit()

                logger.info(f"Worker {worker_id} executing job {job.id} ({job.task_name})...")
                
                job.status = "PROCESSING"
                db.session.commit()

                task_fn = get_task(job.task_name)
                # Task function manages checkpoints internally
                task_fn(job_id=job.id, **(job.payload or {}))

                # After execution, fetch job again and mark succeeded if not failed
                job = db.session.get(JobQueue, job.id)
                if job and job.status != "FAILED":
                    job.status = "SUCCEEDED"
                db.session.commit()
                logger.info(f"Job {job.id} completed successfully.")

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                try:
                    db.session.rollback()
                    if 'job' in locals() and job and hasattr(job, 'id'):
                        job = db.session.get(JobQueue, job.id)
                        if job:
                            job.status = "DEAD" if job.attempts >= 3 else "FAILED"
                            db.session.commit()
                except Exception:
                    pass
                time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_worker()
