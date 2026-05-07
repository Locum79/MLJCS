from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class CertificateType(db.Model):
    __tablename__ = 'certificate_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    period = db.Column(db.String(100), nullable=False)
    master_pdf_path = db.Column(db.String(500), nullable=False)
    master_file_type = db.Column(db.String(10), default='pdf')  # 'pdf' or 'png'
    overlay_coords = db.Column(db.JSON, nullable=False)
    registration_token = db.Column(db.String(100), unique=True, nullable=False)
    # Default email message template (supports {first_name}, {full_name}, {cert_name}, {cert_id})
    email_message = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='certificate_type', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    other_name = db.Column(db.String(100))
    email = db.Column(db.String(255), nullable=False)
    certificate_type_id = db.Column(db.Integer, db.ForeignKey('certificate_types.id'), nullable=False)
    status = db.Column(db.String(20), default='registered')
    certificate_id = db.Column(db.String(50), unique=True)
    include_qr = db.Column(db.Boolean, default=False)   # admin toggles per participant
    approved_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Binary archive: stores cert_id + full_name + issued_date even after record deletion
    cert_archive = db.Column(db.LargeBinary, nullable=True)

    @property
    def full_name(self):
        parts = [self.first_name, self.other_name or '', self.surname]
        return ' '.join(p for p in parts if p.strip())

    @property
    def initials(self):
        parts = [self.first_name, self.surname]
        return ''.join(p[0].upper() for p in parts if p)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    performed_by = db.Column(db.String(100))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CertArchive(db.Model):
    """Permanent record — survives user deletion. Enables QR verification."""
    __tablename__ = 'cert_archive'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(300), nullable=False)
    cert_name = db.Column(db.String(200), nullable=False)
    issued_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='issued')
    raw_binary = db.Column(db.LargeBinary, nullable=True)  # binary blob of cert data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'certificate_id': self.certificate_id,
            'full_name': self.full_name,
            'cert_name': self.cert_name,
            'issued_date': self.issued_date,
            'status': self.status,
        }


class EmailDraft(db.Model):
    __tablename__ = 'email_drafts'
    id = db.Column(db.Integer, primary_key=True)
    cert_type_id = db.Column(db.Integer, db.ForeignKey('certificate_types.id'), nullable=True)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
