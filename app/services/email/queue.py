"""
Email queue manager.
Creates EmailLog records and enqueues RQ jobs with rate limiting support.
All email dispatches go through here — never enqueue worker tasks directly.
"""
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# Statuses
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
    send_rate: int = 15,          # emails per minute
) -> str:
    """
    Queue a single certificate dispatch job.
    Returns the EmailLog id as string.
    """
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
    """
    Queue a batch of certificate dispatch jobs with staggered scheduling.
    Returns count of jobs queued.
    """
    from flask import current_app
    from app.models import db, EmailLog, User
    import math

    delay_seconds = 60.0 / max(send_rate, 1)
    queued = 0

    for i, uid in enumerate(user_ids):
        user = db.session.get(User, uid)
        if not user or user.status != 'approved':
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

        # Stagger: each job delayed by i * delay_seconds
        from rq import Queue
        from datetime import timedelta
        current_app.task_queue.enqueue_in(
            timedelta(seconds=math.floor(i * delay_seconds)),
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
    """Queue a campaign (Mode B) email batch."""
    from flask import current_app
    from app.models import db, EmailLog, User
    import math
    from datetime import timedelta

    delay_seconds = 60.0 / max(send_rate, 1)
    queued = 0
    now = datetime.utcnow()
    base_delay = max(0, (scheduled_at - now).total_seconds()) if scheduled_at else 0

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

        total_delay = base_delay + math.floor(i * delay_seconds)
        current_app.task_queue.enqueue_in(
            timedelta(seconds=total_delay),
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
    """Re-enqueue failed email logs for retry."""
    from flask import current_app
    from app.models import db, EmailLog

    retried = 0
    for lid in log_ids:
        log = db.session.get(EmailLog, lid)
        if not log or log.status not in (FAILED, 'bounced'):
            continue
        log.status = RETRYING
        log.retry_count = (log.retry_count or 0) + 1
        db.session.flush()

        job_fn = ('app.services.email.jobs.send_certificate_job'
                  if log.email_type == 'certificate'
                  else 'app.services.email.jobs.send_campaign_job')

        kwargs = {'log_id': log.id, 'user_id': log.user_id,
                  'draft_id': log.draft_id, 'job_timeout': 300}
        if log.email_type == 'certificate':
            kwargs['cert_type_id'] = log.cert_type_id
        else:
            kwargs['campaign_id'] = log.campaign_id

        current_app.task_queue.enqueue(job_fn, **kwargs)
        retried += 1

    db.session.commit()
    return retried
