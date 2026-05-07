import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app


DEFAULT_SUBJECT = "Your {cert_name} Certificate — MLJ"

DEFAULT_BODY = """Dear {first_name},

Congratulations on successfully completing {cert_name}!

Please find your certificate attached to this email.

Certificate ID: {cert_id}
Issued: {issued_date}

This certificate has been issued by Medical Locum Jobs and serves as official confirmation of your achievement.

Warm regards,
Medical Locum Jobs Team
https://medicalocumjobs.com"""


def _render(template: str, context: dict) -> str:
    """Safe template rendering — replaces {key} placeholders."""
    for key, val in context.items():
        template = template.replace('{' + key + '}', str(val))
    return template


def send_certificate_email(
    to_email: str,
    recipient_name: str,
    full_name: str,
    certificate_name: str,
    pdf_bytes: bytes,
    certificate_id: str,
    issued_date: str,
    subject_template: str = None,
    body_template: str = None
):
    context = {
        'first_name': recipient_name,
        'full_name': full_name,
        'cert_name': certificate_name,
        'cert_id': certificate_id,
        'issued_date': issued_date,
    }

    subject = _render(subject_template or DEFAULT_SUBJECT, context)
    body = _render(body_template or DEFAULT_BODY, context)

    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{certificate_id}.pdf"')
    msg.attach(part)

    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)


def send_nudge(to_email: str, recipient_name: str, certificate_name: str):
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = f"Reminder: {certificate_name} — MLJ"

    body = f"""Dear {recipient_name},

This is a friendly reminder regarding your {certificate_name} certificate from Medical Locum Jobs.

If you have any questions, please don't hesitate to get in touch.

Warm regards,
Medical Locum Jobs Team"""

    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)
