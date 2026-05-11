import smtplib
import logging
import time
import socket
import json
import base64
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict
from flask import current_app

logger = logging.getLogger(__name__)


def _force_ipv4(host: str) -> str:
    """Force resolution to IPv4 to avoid 'Network is unreachable' on IPv6 stacks."""
    try:
        # Get the first IPv4 address
        addr_info = socket.getaddrinfo(host, None, socket.AF_INET)
        if addr_info:
            return addr_info[0][4][0]
    except Exception as e:
        logger.debug(f"IPv4 resolution failed for {host}: {e}")
    return host


def _smtp_connection():
    cfg = current_app.config
    host = cfg['MAIL_SERVER']
    port = cfg['MAIL_PORT']
    
    # Many cloud providers (Railway, etc.) have flaky IPv6 routing for SMTP
    # Forcing IPv4 often resolves [Errno 101] Network is unreachable
    resolved_host = _force_ipv4(host)
    if resolved_host != host:
        logger.debug(f"Resolved {host} to {resolved_host} (IPv4)")
    
    use_ssl = cfg.get('MAIL_USE_SSL', False)
    use_tls = cfg.get('MAIL_USE_TLS', True)

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(resolved_host, port, timeout=30)
        else:
            server = smtplib.SMTP(resolved_host, port, timeout=30)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
        
        server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        return server
    except Exception as e:
        logger.error(f"Failed to connect to SMTP {host}:{port} (resolved: {resolved_host}): {e}")
        raise


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


def _dispatch_sendgrid(
    api_key: str,
    to_email: str,
    subject: str,
    body: str,
    from_name: str,
    from_email: str,
    reply_to: str = '',
    attachments: List[Dict] = None,
) -> Dict:
    """Send email via SendGrid Web API (Bypasses SMTP port blocking)."""
    url = "https://api.sendgrid.com/v3/mail/send"
    
    # Construct SendGrid JSON payload
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": from_email, "name": from_name},
        "content": [{"type": "text/plain", "value": body}]
    }
    
    if reply_to:
        payload["reply_to"] = {"email": reply_to}
        
    if attachments:
        payload["attachments"] = []
        for att in attachments:
            payload["attachments"].append({
                "content": base64.b64encode(att['data']).decode('utf-8'),
                "filename": att['filename'],
                "type": "application/pdf",
                "disposition": "attachment"
            })

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.getcode() in [200, 201, 202]:
                return {'success': True, 'error': None, 'attempts': 1}
            return {'success': False, 'error': f"SendGrid error: {response.getcode()}", 'attempts': 1}
    except Exception as e:
        return {'success': False, 'error': str(e), 'attempts': 1}


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
    # 1. Try SendGrid API first if configured (Bypasses Railway Firewall)
    api_key = current_app.config.get('SENDGRID_API_KEY')
    if api_key:
        logger.debug(f"Using SendGrid API for {to_email}")
        result = _dispatch_sendgrid(api_key, to_email, subject, body, from_name, from_email, reply_to, attachments)
        if result['success']:
            logger.info(f"Email sent via SendGrid API → {to_email}")
            return result
        logger.warning(f"SendGrid API failed: {result['error']}. Falling back to SMTP...")

    # 2. Fallback to SMTP
    from_header = f"{from_name} <{from_email}>"
    msg = _build_message(to_email, subject, body, from_header, reply_to, attachments)

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with _smtp_connection() as server:
                server.send_message(msg)
            logger.info(f"Email sent via SMTP → {to_email} (attempt {attempt})")
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


def dispatch_or_raise(*args, **kwargs):
    result = dispatch(*args, **kwargs)
    if not result['success']:
        raise Exception(f"Email dispatch failed: {result['error']}")
    return result
