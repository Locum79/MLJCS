from flask_mail import Message
from flask import current_app
from app.utils.templates import render, DEFAULT_CERT_SUBJECT, DEFAULT_CERT_BODY

def send_certificate_email(to_email, first_name, full_name, course_name, pdf_bytes, certificate_id, issue_date, verify_url='', org_name='Medical Locum Jobs', sender_name='Medical Locum Jobs Academy', reply_to='', subject_tpl=None, body_tpl=None, include_attachment=True):
    from app import mail
    ctx = {
        'first_name': first_name,
        'full_name': full_name,
        'course_name': course_name,
        'certificate_id': certificate_id,
        'issue_date': issue_date,
        'organization_name': org_name,
        'verification_link': verify_url
    }
    subject = render(subject_tpl or DEFAULT_CERT_SUBJECT, ctx)
    body = render(body_tpl or DEFAULT_CERT_BODY, ctx)
    
    msg = Message(
        subject=subject,
        recipients=[to_email],
        body=body,
        sender=(sender_name, current_app.config.get('MAIL_USERNAME', ''))
    )
    if reply_to:
        msg.reply_to = reply_to
    
    import uuid
    message_id = str(uuid.uuid4())
    if not hasattr(msg, 'extra_headers') or msg.extra_headers is None:
        msg.extra_headers = {}
    msg.extra_headers['X-Dispatch-Message-ID'] = message_id

    if include_attachment and pdf_bytes:
        msg.attach(f"{certificate_id}.pdf", "application/pdf", pdf_bytes)
    
    try:
        mail.send(msg)
        return message_id
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise

def send_nudge(to_email, first_name, course_name, org_name='Medical Locum Jobs'):
    from app import mail
    body = f"Dear {first_name},\n\nThis is a reminder regarding your {course_name} certificate.\n\nWarm regards,\n{org_name}"
    msg = Message(
        subject=f"Reminder: {course_name}",
        recipients=[to_email],
        body=body,
        sender=(org_name, current_app.config.get('MAIL_USERNAME', ''))
    )
    mail.send(msg)

def send_generic_email(to_email, subject, body, reply_to=None):
    from app import mail
    msg = Message(
        subject=subject,
        recipients=[to_email],
        body=body,
        sender=current_app.config.get('MAIL_USERNAME', '')
    )
    if reply_to:
        msg.reply_to = reply_to
    mail.send(msg)
