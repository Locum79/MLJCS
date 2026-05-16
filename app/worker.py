import logging
import json
from datetime import datetime
logger = logging.getLogger(__name__)


def _get_org_settings(app_context):
    from app.models import OrgSettings
    settings = OrgSettings.query.first()
    if not settings:
        settings = OrgSettings()
    return settings


def generate_and_send_certificate(job_id: int, user_id: int, certificate_type_id: int, draft_id: int = None):
    from app import create_app
    from app.models import db, User, CertificateType, CertArchive, AuditLog, EmailDraft, JobQueue
    from app.engine.pdf_processor import generate_personalized_pdf
    from app.engine.email_sender import send_certificate_email
    from app.domain.certificates.service import resolve_certificate_asset
    from app.engine.cert_id import assign_certificate_id

    app = create_app()
    with app.app_context():
        job = db.session.get(JobQueue, job_id)
        if not job:
            return

        try:
            user = db.session.get(User, user_id)
            cert_type = db.session.get(CertificateType, certificate_type_id)
            org = _get_org_settings(None)

            if not user or not cert_type:
                raise RuntimeError("Missing User or CertificateType")

            if job.checkpoint == "INIT" or job.checkpoint == "PENDING":
                if not user.certificate_id:
                    assign_certificate_id(user)
                    db.session.commit()
                job.checkpoint = "ASSET_RESOLVED"
                db.session.commit()

            issue_date = (user.sent_at or datetime.utcnow()).strftime('%d %B %Y')
            base_url = org.verify_base_url or ''
            verify_url = f'{base_url}/verify/{user.certificate_id}' if base_url and user.certificate_id else ''

            if job.checkpoint == "ASSET_RESOLVED":
                template_binary = resolve_certificate_asset(cert_type)
                pdf_bytes = generate_personalized_pdf(
                    template_binary=template_binary, 
                    overlay_coords=cert_type.overlay_coords, 
                    full_name=user.full_name, 
                    certificate_id=user.certificate_id,
                    issuance_date=issue_date, 
                    include_qr=user.include_qr, 
                    cert_name=cert_type.name, 
                    master_file_type=cert_type.master_file_type or 'pdf', 
                    verify_url=verify_url
                )
                
                archive = CertArchive.query.filter_by(certificate_id=user.certificate_id).first()
                if not archive:
                    archive = CertArchive(
                        certificate_id=user.certificate_id, 
                        full_name=user.full_name, 
                        cert_name=cert_type.name, 
                        course_code=cert_type.course_code, 
                        issued_date=issue_date,
                        email=user.email, 
                        status='issued', 
                        raw_binary=json.dumps({'email': user.email, 'cert_type_id': cert_type.id, 'include_qr': user.include_qr}).encode('utf-8'),
                        pdf_binary=pdf_bytes
                    )
                    db.session.add(archive)
                else:
                    archive.pdf_binary = pdf_bytes
                
                job.checkpoint = "OUTPUT_STORED"
                db.session.commit()

            if job.checkpoint == "OUTPUT_STORED":
                archive = CertArchive.query.filter_by(certificate_id=user.certificate_id).first()
                if not archive or not archive.pdf_binary:
                    raise RuntimeError("PDF output missing during email phase")

                pdf_bytes = archive.pdf_binary
                subject_tpl = body_tpl = None
                if draft_id:
                    draft = db.session.get(EmailDraft, draft_id)
                    if draft:
                        subject_tpl = draft.subject
                        body_tpl = draft.body
                elif cert_type.email_message:
                    body_tpl = cert_type.email_message
                if cert_type.email_subject:
                    subject_tpl = cert_type.email_subject

                send_certificate_email(
                    to_email=user.email, 
                    first_name=user.first_name, 
                    full_name=user.full_name, 
                    course_name=cert_type.name, 
                    pdf_bytes=pdf_bytes, 
                    certificate_id=user.certificate_id,
                    issue_date=issue_date, 
                    verify_url=verify_url, 
                    org_name=org.org_name, 
                    sender_name=org.sender_name, 
                    reply_to=org.reply_to_email, 
                    subject_tpl=subject_tpl, 
                    body_tpl=body_tpl, 
                    include_attachment=True
                )

                user.status = 'sent'
                db.session.add(AuditLog(user_id=user.id, action='sent', performed_by='system', details={'cert_id': user.certificate_id, 'email': user.email}))
                
                job.checkpoint = "EMAIL_SENT"
                db.session.commit()
                logger.info(f'Certificate sent and job marked EMAIL_SENT: {user.certificate_id} → {user.email}')

        except Exception as e:
            logger.error(f'Certificate send failed user_id={user_id}: {e}', exc_info=True)
            try:
                db.session.rollback()
                job = db.session.get(JobQueue, job_id)
                if job:
                    job.status = "FAILED"
                user = db.session.get(User, user_id)
                if user and user.status != 'sent':
                    user.status = 'approved'
                db.session.add(AuditLog(user_id=user_id, action='send_failed', performed_by='system', details={'error': str(e)}))
                db.session.commit()
            except Exception:
                pass
            raise


def send_nudge_email(job_id: int, user_id: int):
    from app import create_app
    from app.models import db, User, CertificateType, JobQueue
    from app.engine.email_sender import send_nudge
    app = create_app()
    with app.app_context():
        job = db.session.get(JobQueue, job_id)
        if job and job.checkpoint == "EMAIL_SENT":
            return
            
        user = db.session.get(User, user_id)
        cert_type = db.session.get(CertificateType, user.certificate_type_id)
        org = _get_org_settings(None)
        send_nudge(user.email, user.first_name, cert_type.name, org.org_name)
        
        if job:
            job.checkpoint = "EMAIL_SENT"
            db.session.commit()


def process_campaign(job_id: int, campaign_id: int, user_ids: list, draft_id: int):
    from app import create_app
    from app.models import db, Campaign, User, EmailDraft, JobQueue
    from app.engine.email_sender import send_generic_email
    from app.utils.templates import render
    app = create_app()
    with app.app_context():
        job = db.session.get(JobQueue, job_id)
        if job and job.checkpoint == "COMPLETED":
            return
            
        campaign = db.session.get(Campaign, campaign_id)
        draft = db.session.get(EmailDraft, draft_id)
        org = _get_org_settings(None)
        base_url = (org.verify_base_url or '').rstrip('/')
        if not campaign or not draft:
            logger.error(f'process_campaign: missing campaign={campaign_id} or draft={draft_id}')
            return
            
        sent = failed = 0
        for uid in user_ids:
            user = db.session.get(User, uid)
            if not user or user.unsubscribed:
                continue
            try:
                ctx = {
                    'first_name': user.first_name,
                    'full_name': user.full_name,
                    'organization_name': org.org_name,
                    'verification_link': f"{base_url}/verify/{user.certificate_id}" if user.certificate_id else "",
                    'certificate_id': user.certificate_id or "",
                }
                subject = render(draft.subject, ctx)
                body = render(draft.body, ctx)
                send_generic_email(
                    to_email=user.email,
                    subject=subject,
                    body=body,
                    reply_to=org.reply_to_email
                )
                sent += 1
            except Exception as e:
                logger.error(f'Campaign email exception uid={uid}: {e}')
                failed += 1
                
        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.status = 'sent'
        campaign.sent_at = datetime.utcnow()
        if job:
            job.checkpoint = "COMPLETED"
        db.session.commit()


def process_bulk_certificates(job_id: int, user_ids: list, certificate_type_id: int, draft_id: int = None):
    from app import create_app
    from app.models import db, JobQueue
    app = create_app()
    with app.app_context():
        job = db.session.get(JobQueue, job_id)
        if job and job.checkpoint == "COMPLETED":
            return
            
        for uid in user_ids:
            try:
                pass
            except Exception as e:
                pass
                
        from flask import current_app
        for uid in user_ids:
            current_app.task_queue.enqueue(
                'generate_and_send_certificate', 
                idempotency_key=f"cert_{uid}_{certificate_type_id}", 
                user_id=uid, 
                certificate_type_id=certificate_type_id, 
                draft_id=draft_id
            )
            
        if job:
            job.checkpoint = "COMPLETED"
            db.session.commit()


__all__ = ["process_bulk_certificates", "generate_and_send_certificate", "process_campaign", "send_nudge_email"]
