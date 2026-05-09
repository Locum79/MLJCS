"""
Legacy shim — kept for backward compatibility.
All new code uses app.services.email directly.
"""
from app.services.email.sender import dispatch
from app.services.email.templates import render, DEFAULT_CERT_SUBJECT, DEFAULT_CERT_BODY
from flask import current_app


def send_certificate_email(to_email, first_name, full_name, course_name,
                            pdf_bytes, certificate_id, issue_date,
                            verify_url='', org_name='Medical Locum Jobs',
                            sender_name='Medical Locum Jobs Academy',
                            reply_to='', subject_tpl=None, body_tpl=None,
                            include_attachment=True):
    ctx = {
        'first_name': first_name, 'full_name': full_name,
        'course_name': course_name, 'certificate_id': certificate_id,
        'issue_date': issue_date, 'organization_name': org_name,
        'verification_link': verify_url,
    }
    subject = render(subject_tpl or DEFAULT_CERT_SUBJECT, ctx)
    body    = render(body_tpl    or DEFAULT_CERT_BODY,    ctx)
    atts = [{'data': pdf_bytes, 'filename': f"{certificate_id}.pdf"}] if include_attachment and pdf_bytes else []
    dispatch(to_email, subject, body,
             from_name=sender_name,
             from_email=current_app.config.get('MAIL_USERNAME', ''),
             reply_to=reply_to,
             attachments=atts)


def send_nudge(to_email, first_name, course_name, org_name='Medical Locum Jobs'):
    body = f"Dear {first_name},\n\nThis is a reminder regarding your {course_name} certificate.\n\nWarm regards,\n{org_name}"
    dispatch(to_email, f"Reminder: {course_name}",
             body, from_name=org_name,
             from_email=current_app.config.get('MAIL_USERNAME', ''))
