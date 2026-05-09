from typing import Dict, List
from datetime import datetime, timedelta


def summary_stats(cert_type_id: int = None) -> Dict:
    from app.models import EmailLog, db
    q = EmailLog.query
    if cert_type_id:
        q = q.filter_by(cert_type_id=cert_type_id)

    total     = q.count()
    sent      = q.filter_by(status='sent').count()
    failed    = q.filter_by(status='failed').count()
    pending   = q.filter(EmailLog.status.in_(['pending', 'processing', 'retrying'])).count()
    cancelled = q.filter_by(status='cancelled').count()

    return {
        'total': total, 'sent': sent, 'failed': failed,
        'pending': pending, 'cancelled': cancelled,
        'success_rate': round(sent / total * 100, 1) if total else 0,
    }


def failed_logs(limit: int = 100) -> List[Dict]:
    from app.models import EmailLog
    logs = EmailLog.query.filter(
        EmailLog.status.in_(['failed', 'bounced'])
    ).order_by(EmailLog.created_at.desc()).limit(limit).all()

    return [{
        'id': l.id,
        'recipient_email': l.recipient_email,
        'recipient_name': l.recipient_name,
        'email_type': l.email_type,
        'failed_reason': l.failed_reason or '',
        'retry_count': l.retry_count or 0,
        'created_at': l.created_at.strftime('%d/%m/%Y %H:%M') if l.created_at else '',
    } for l in logs]


def campaign_stats(campaign_id: int) -> Dict:
    from app.models import EmailLog
    logs = EmailLog.query.filter_by(campaign_id=campaign_id).all()
    total   = len(logs)
    sent    = sum(1 for l in logs if l.status == 'sent')
    failed  = sum(1 for l in logs if l.status == 'failed')
    pending = sum(1 for l in logs if l.status in ('pending', 'processing'))
    return {
        'total': total, 'sent': sent, 'failed': failed, 'pending': pending,
        'progress': round(sent / total * 100) if total else 0,
    }
