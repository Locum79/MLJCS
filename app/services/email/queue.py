import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

PENDING    = 'pending'
PROCESSING = 'processing'
SENT       = 'sent'
FAILED     = 'failed'
RETRYING   = 'retrying'
CANCELLED  = 'cancelled'
SCHEDULED  = 'scheduled'


def enqueue_certificate(
    user_id: int,
    cert_type_id: int,
    draft_id: Optional[int] = None,
    send_rate: int = 15,
) -> str:
    from flask import current_app
    from app.models import db, EmailLog, User

    user = db.session.get(User, user_id)
    if not user:
        return ''

    log = EmailLog(
        recipient_email=user.email,
        recipient_name=user.full_name,
        email_type='certificate',
        status=PENDING,
        user_id=user_id,
        cert_type_id=cert_type_id,
        draft_id=draft_id,
    )
    db.session.add(log)
    db.session.commit()

    current_app.task_queue.enqueue(
        'app.services.email.jobs.send_certificate_job',
        log_id=log.id,
        user_id=user_id,
        cert_type_id=cert_type_id,
        draft_id=draft_id,
        job_timeout=300,
    )
    return str(log.id)


def enqueue_batch(
    user_ids: List[int],
    cert_type_id: int,
    draft_id: Optional[int],
    send_rate: int = 15,
) -> int:
    from flask import current_app
    from app.models import db, EmailLog, User

    delay_seconds = 60.0 / max(send_rate, 1)
    queued = 0

    for i, uid in enumerate(user_ids):
        user = db.session.get(User, uid)
        if not user or user.status not in ('approved', 'sending'):
            continue

        log = EmailLog(
            recipient_email=user.email,
            recipient_name=user.full_name,
            email_type='certificate',
            status=PENDING,
            user_id=uid,
            cert_type_id=cert_type_id,
            draft_id=draft_id,
        )
        db.session.add(log)
        db.session.flush()

        delay = timedelta(seconds=math.floor(i * delay_seconds))
        if delay.total_seconds() > 0:
            current_app.task_queue.enqueue_in(
                delay,
                'app.services.email.jobs.send_certificate_job',
                log_id=log.id,
                user_id=uid,
                cert_type_id=cert_type_id,
                draft_id=draft_id,
                job_timeout=300,
            )
        else:
            current_app.task_queue.enqueue(
                'app.services.email.jobs.send_certificate_job',
                log_id=log.id,
                user_id=uid,
                cert_type_id=cert_type_id,
                draft_id=draft_id,
                job_timeout=300,
            )
        queued += 1

    db.session.commit()
    logger.info(f"Queued {queued} certificate emails (rate={send_rate}/min)")
    return queued


def enqueue_campaign_batch(
    campaign_id: int,
    user_ids: List[int],
    draft_id: int,
    send_rate: int = 15,
    scheduled_at: Optional[datetime] = None,
) -> int:
    from flask import current_app
    from app.models import db, EmailLog, User

    delay_seconds = 60.0 / max(send_rate, 1)
    queued = 0
    now = datetime.utcnow()
    base_delay = max(0.0, (scheduled_at - now).total_seconds()) if scheduled_at else 0.0

    for i, uid in enumerate(user_ids):
        user = db.session.get(User, uid)
        if not user or user.unsubscribed:
            continue

        log = EmailLog(
            recipient_email=user.email,
            recipient_name=user.full_name,
            email_type='campaign',
            status=PENDING if not scheduled_at else SCHEDULED,
            user_id=uid,
            cert_type_id=None,
            draft_id=draft_id,
            campaign_id=campaign_id,
        )
        db.session.add(log)
        db.session.flush()

        total_delay = timedelta(seconds=math.floor(base_delay + i * delay_seconds))
        if total_delay.total_seconds() > 0:
            current_app.task_queue.enqueue_in(
                total_delay,
                'app.services.email.jobs.send_campaign_job',
                log_id=log.id,
                user_id=uid,
                draft_id=draft_id,
                campaign_id=campaign_id,
                job_timeout=120,
            )
        else:
            current_app.task_queue.enqueue(
                'app.services.email.jobs.send_campaign_job',
                log_id=log.id,
                user_id=uid,
                draft_id=draft_id,
                campaign_id=campaign_id,
                job_timeout=120,
            )
        queued += 1

    db.session.commit()
    logger.info(f"Queued {queued} campaign emails (rate={send_rate}/min)")
    return queued


def retry_failed(log_ids: List[int]) -> int:
    from flask import current_app
    from app.models import db, EmailLog

    retried = 0
    for lid in log_ids:
        log = db.session.get(EmailLog, lid)
        if not log or log.status not in (FAILED, 'bounced', RETRYING):
            continue
        log.status = RETRYING
        log.retry_count = (log.retry_count or 0) + 1
        db.session.flush()

        if log.email_type == 'certificate':
            current_app.task_queue.enqueue(
                'app.services.email.jobs.send_certificate_job',
                log_id=log.id,
                user_id=log.user_id,
                cert_type_id=log.cert_type_id,
                draft_id=log.draft_id,
                job_timeout=300,
            )
        else:
            current_app.task_queue.enqueue(
                'app.services.email.jobs.send_campaign_job',
                log_id=log.id,
                user_id=log.user_id,
                draft_id=log.draft_id,
                campaign_id=log.campaign_id,
                job_timeout=120,
            )
        retried += 1

    db.session.commit()
    return retried

