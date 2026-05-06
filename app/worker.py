from app import create_app
from app.models import db, User, CertificateType, AuditLog
import logging

logger = logging.getLogger(__name__)

def generate_and_send_certificate(user_id, certificate_type_id):
    from app.engine.pdf_processor import generate_personalized_pdf
    from app.engine.email_sender import send_certificate_email
    
    app = create_app()
    with app.app_context():
        try:
            user = db.session.get(User, user_id)
            cert_type = db.session.get(CertificateType, certificate_type_id)
            
            full_name = f"{user.first_name} {user.surname}"
            if user.other_name and user.other_name.strip():
                full_name += f" {user.other_name}"
            
            pdf_bytes = generate_personalized_pdf(
                master_pdf_path=cert_type.master_pdf_path,
                overlay_coords=cert_type.overlay_coords,
                full_name=full_name.strip(),
                certificate_id=user.certificate_id,
                issuance_date=user.sent_at.strftime('%B %d, %Y') if user.sent_at else ''
            )
            
            send_certificate_email(
                to_email=user.email,
                recipient_name=user.first_name,
                certificate_name=cert_type.name,
                pdf_bytes=pdf_bytes,
                certificate_id=user.certificate_id
            )
            
            db.session.add(AuditLog(
                user_id=user.id,
                action='sent',
                performed_by='system',
                details={'status': 'success'}
            ))
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed user {user_id}: {str(e)}")
            try:
                db.session.add(AuditLog(
                    user_id=user_id,
                    action='send_failed',
                    performed_by='system',
                    details={'error': str(e)}
                ))
                db.session.commit()
            except:
                pass
            raise

def send_nudge_email(user_id):
    from app.engine.email_sender import send_nudge
    
    app = create_app()
    with app.app_context():
        user = db.session.get(User, user_id)
        cert_type = db.session.get(CertificateType, user.certificate_type_id)
        send_nudge(user.email, user.first_name, cert_type.name)
