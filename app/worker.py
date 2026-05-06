from app import db
from app.models import User, CertificateType, AuditLog

def generate_and_send_certificate(user_id, certificate_type_id):
    from app.engine.pdf_processor import generate_personalized_pdf
    from app.engine.email_sender import send_certificate_email
    from flask import current_app
    
    with current_app.app_context():
        try:
            user = User.query.get(user_id)
            cert_type = CertificateType.query.get(certificate_type_id)
            
            pdf_bytes = generate_personalized_pdf(
                master_pdf_path=cert_type.master_pdf_path,
                overlay_coords=cert_type.overlay_coords,
                full_name=f"{user.first_name} {user.surname}",
                certificate_id=user.certificate_id,
                issuance_date=user.sent_at.strftime('%B %d, %Y')
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
            db.session.add(AuditLog(
                user_id=user_id,
                action='send_failed',
                performed_by='system',
                details={'error': str(e)}
            ))
            db.session.commit()
            raise

def send_nudge_email(user_id):
    from app.engine.email_sender import send_nudge
    from flask import current_app
    
    with current_app.app_context():
        user = User.query.get(user_id)
        cert_type = CertificateType.query.get(user.certificate_type_id)
        send_nudge(user.email, user.first_name, cert_type.name)
