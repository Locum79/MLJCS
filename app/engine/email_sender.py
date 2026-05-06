import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app

def send_certificate_email(to_email, recipient_name, certificate_name, pdf_bytes, certificate_id):
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = f"Your {certificate_name} Certificate"
    
    body = f"""Dear {recipient_name},

Congratulations! Your certificate for {certificate_name} is ready.

Certificate ID: {certificate_id}

Your certificate is attached to this email.

Best regards,
Medical Locum Jobs Team"""
    
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

def send_nudge(to_email, recipient_name, certificate_name):
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = f"Reminder: {certificate_name}"
    
    body = f"""Dear {recipient_name},

This is a reminder regarding your {certificate_name} certificate.

Please complete any pending steps.

Best regards,
Medical Locum Jobs Team"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)
