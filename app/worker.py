from app import create_app
from app.models import db, User, CertificateType, AuditLog, CertArchive
from app.engine.luhn import generate_certificate_id
import logging
import json

logger = logging.getLogger(__name__)


def _next_sequence(cert_type_id: int) -> int:
    """Get next sequence number for this cert type."""
    count = User.query.filter_by(
        certificate_type_id=cert_type_id
    ).filter(User.certificate_id.isnot(None)).count()
    return count + 1


def generate_and_send_certificate(user_id, certificate_type_id):
    from app.engine.pdf_processor import generate_personalized_pdf
    from app.engine.email_sender import send_certificate_email
    from datetime import datetime

    app = create_app()
    with app.app_context():
        try:
            user = db.session.get(User, user_id)
            cert_type = db.session.get(CertificateType, certificate_type_id)

            # Generate Luhn ID if not already assigned
            if not user.certificate_id:
                seq = _next_sequence(certificate_type_id)
                user.certificate_id = generate_certificate_id(
                    user.first_name, user.surname, seq, user.sent_at or datetime.utcnow()
                )
                db.session.flush()

            issued_date = (user.sent_at or datetime.utcnow()).strftime('%d %B %Y')

            # Resolve email template from draft or cert type default
            subject_tpl = None
            body_tpl = None
            if cert_type.email_message:
                body_tpl = cert_type.email_message

            pdf_bytes = generate_personalized_pdf(
                master_pdf_path=cert_type.master_pdf_path,
                overlay_coords=cert_type.overlay_coords,
                full_name=user.full_name,
                certificate_id=user.certificate_id,
                issuance_date=issued_date,
                include_qr=user.include_qr,
                cert_name=cert_type.name,
                master_file_type=cert_type.master_file_type or 'pdf'
            )

            send_certificate_email(
                to_email=user.email,
                recipient_name=user.first_name,
                full_name=user.full_name,
                certificate_name=cert_type.name,
                pdf_bytes=pdf_bytes,
                certificate_id=user.certificate_id,
                issued_date=issued_date,
                subject_template=subject_tpl,
                body_template=body_tpl
            )

            # Persist to permanent archive
            archive_payload = json.dumps({
                'certificate_id': user.certificate_id,
                'full_name': user.full_name,
                'cert_name': cert_type.name,
                'issued_date': issued_date,
                'email': user.email,
                'status': 'issued'
            }).encode('utf-8')

            existing = CertArchive.query.filter_by(certificate_id=user.certificate_id).first()
            if not existing:
                db.session.add(CertArchive(
                    certificate_id=user.certificate_id,
                    full_name=user.full_name,
                    cert_name=cert_type.name,
                    issued_date=issued_date,
                    status='issued',
                    raw_binary=archive_payload
                ))

            db.session.add(AuditLog(
                user_id=user.id,
                action='sent',
                performed_by='system',
                details={'status': 'success', 'cert_id': user.certificate_id}
            ))
            db.session.commit()

        except Exception as e:
            logger.error(f"Failed user {user_id}: {str(e)}")
            try:
                db.session.rollback()
                db.session.add(AuditLog(
                    user_id=user_id,
                    action='send_failed',
                    performed_by='system',
                    details={'error': str(e)}
                ))
                db.session.commit()
            except Exception:
                pass
            raise


def send_nudge_email(user_id):
    from app.engine.email_sender import send_nudge

    app = create_app()
    with app.app_context():
        user = db.session.get(User, user_id)
        cert_type = db.session.get(CertificateType, user.certificate_type_id)
        send_nudge(user.email, user.first_name, cert_type.name)
