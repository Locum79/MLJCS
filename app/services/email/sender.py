import smtplib
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict
from flask import current_app

logger = logging.getLogger(__name__)


def _smtp_connection():
    cfg = current_app.config
    server = smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=30)
    server.ehlo()
    if cfg.get('MAIL_USE_TLS', True):
        server.starttls()
        server.ehlo()
    server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
    return server


def _build_message(
    to_email: str,
    subject: str,
    body_text: str,
    from_header: str,
    reply_to: str = '',
    attachments: List[Dict] = None,
) -> MIMEMultipart:
    msg = MIMEMultipart('mixed')
    msg['From']    = from_header
    msg['To']      = to_email
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(body_text, 'plain', 'utf-8'))
    msg.attach(alt)

    for att in (attachments or []):
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(att['data'])
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f"attachment; filename=\"{att['filename']}\""
        )
        msg.attach(part)

    return msg


def dispatch(
    to_email: str,
    subject: str,
    body: str,
    from_name: str,
    from_email: str,
    reply_to: str = '',
    attachments: List[Dict] = None,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> Dict:
    from_header = f"{from_name} <{from_email}>"
    msg = _build_message(to_email, subject, body, from_header, reply_to, attachments)

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with _smtp_connection() as server:
                server.send_message(msg)
            logger.info(f"Email sent → {to_email} (attempt {attempt})")
            return {'success': True, 'error': None, 'attempts': attempt}
        except smtplib.SMTPRecipientsRefused as e:
            logger.warning(f"Hard bounce {to_email}: {e}")
            return {'success': False, 'error': f'bounced:{str(e)}', 'attempts': attempt}
        except Exception as e:
            last_error = str(e)
            logger.warning(f"SMTP attempt {attempt} failed for {to_email}: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    return {'success': False, 'error': last_error, 'attempts': max_retries}
