"""
Email dispatch engine.
Supports Mode A (cert attachment) and Mode B (communication only).
Handles sender identity, reply-to, and smart template rendering.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app

logger = logging.getLogger(__name__)

TEMPLATE_VARS = [
    '{{full_name}}', '{{first_name}}', '{{certificate_id}}',
    '{{course_name}}', '{{issue_date}}', '{{organization_name}}',
    '{{verification_link}}'
]

DEFAULT_SUBJECT = "Your {{course_name}} Certificate — {{organization_name}}"

DEFAULT_BODY = """Dear {{first_name}},

Congratulations on successfully completing {{course_name}}!

Please find your personalised certificate attached to this email.

Certificate ID: {{certificate_id}}
Issued: {{issue_date}}

You can verify the authenticity of this certificate at:
{{verification_link}}

This certificate is issued by {{organization_name}} as official confirmation of your achievement. Please retain it for your records.

Warm regards,
{{organization_name}}"""


def _render(template: str, ctx: dict) -> str:
    """Replace {{key}} placeholders with context values."""
    for k, v in ctx.items():
        template = template.replace('{{' + k + '}}', str(v or ''))
    return template


def _smtp_conn():
    cfg = current_app.config
    server = smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'])
    server.ehlo()
    if cfg.get('MAIL_USE_TLS', True):
        server.starttls()
    server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
    return server


def send_certificate_email(
    to_email: str,
    first_name: str,
    full_name: str,
    course_name: str,
    pdf_bytes: bytes,
    certificate_id: str,
    issue_date: str,
    verify_url: str = '',
    org_name: str = 'Medical Locum Jobs',
    sender_name: str = 'Medical Locum Jobs Academy',
    reply_to: str = '',
    subject_tpl: str = None,
    body_tpl: str = None,
    include_attachment: bool = True,
):
    ctx = {
        'first_name': first_name,
        'full_name': full_name,
        'course_name': course_name,
        'certificate_id': certificate_id,
        'issue_date': issue_date,
        'organization_name': org_name,
        'verification_link': verify_url,
    }

    subject = _render(subject_tpl or DEFAULT_SUBJECT, ctx)
    body = _render(body_tpl or DEFAULT_BODY, ctx)

    from_addr = current_app.config.get('MAIL_USERNAME', '')
    from_header = f"{sender_name} <{from_addr}>"

    msg = MIMEMultipart()
    msg['From'] = from_header
    msg['To'] = to_email
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    if include_attachment and pdf_bytes:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        f'attachment; filename="{certificate_id}.pdf"')
        msg.attach(part)

    with _smtp_conn() as server:
        server.send_message(msg)


def send_campaign_email(
    to_email: str,
    context: dict,
    subject_tpl: str,
    body_tpl: str,
    sender_name: str = 'Medical Locum Jobs',
    reply_to: str = '',
    unsubscribe_url: str = '',
):
    """Mode B — communication/campaign email without cert attachment."""
    subject = _render(subject_tpl, context)
    body = _render(body_tpl, context)

    if unsubscribe_url:
        body += f"\n\n---\nTo unsubscribe: {unsubscribe_url}"

    from_addr = current_app.config.get('MAIL_USERNAME', '')
    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{from_addr}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to
    if unsubscribe_url:
        msg['List-Unsubscribe'] = f"<{unsubscribe_url}>"

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with _smtp_conn() as server:
        server.send_message(msg)


def send_nudge(to_email: str, first_name: str, course_name: str,
               org_name: str = 'Medical Locum Jobs'):
    body = f"""Dear {first_name},

This is a friendly reminder regarding your {course_name} certificate from {org_name}.

If you have any questions, please don't hesitate to get in touch.

Warm regards,
{org_name}"""

    from_addr = current_app.config.get('MAIL_USERNAME', '')
    msg = MIMEMultipart()
    msg['From'] = f"{org_name} <{from_addr}>"
    msg['To'] = to_email
    msg['Subject'] = f"Reminder: {course_name} — {org_name}"
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with _smtp_conn() as server:
        server.send_message(msg)
