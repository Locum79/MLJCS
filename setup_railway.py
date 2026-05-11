"""
Seed script: run once after migrations to create admin + sample data.
Usage: python setup_railway.py

NOTE: Schema is managed exclusively by Alembic.
      Run `python migrate.py` (or `alembic upgrade head`) before this script.
"""
from app import create_app, db
from app.models import Admin, CertificateType, User, EmailDraft, CertArchive
from app.engine.luhn import generate_certificate_id
import uuid
import os
from datetime import datetime

app = create_app()

with app.app_context():
    # ── Admin ─────────────────────────────────────────────────────────────
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
    existing = Admin.query.filter_by(email=admin_email).first()
    if not existing:
        admin = Admin(email=admin_email)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Admin created: {admin_email}")
    else:
        existing.set_password(admin_password)
        db.session.commit()
        print(f"✅ Admin password refreshed: {admin_email}")

    # ── Sample Certificate Type ────────────────────────────────────────────
    if CertificateType.query.count() == 0:
        token = str(uuid.uuid4())[:8]
        ct = CertificateType(
            name="Manual Handling Training",
            period="March 2026",
            master_pdf_path="uploads/sample_master.pdf",
            master_file_type="pdf",
            overlay_coords={
                "name_x": 0, "name_y": 380, "name_font_size": 28,
                "cert_id_x": 50, "cert_id_y": 52,
                "date_x": 50, "date_y": 38,
                "qr_x": -1, "qr_y": 30, "qr_size": 90
            },
            registration_token=token,
            email_message=None
        )
        db.session.add(ct)
        db.session.commit()
        print(f"✅ Sample cert type created. Token: {token}")
        print(f"   Register URL: /register/{token}")

        # ── Sample Participants ────────────────────────────────────────────
        now = datetime.utcnow()
        participants = [
            ("John", "Smith", "", "john.smith@example.com", "approved", True),
            ("Mary", "Johnson", "Grace", "mary.johnson@example.com", "approved", False),
            ("David", "Williams", "", "david.williams@example.com", "registered", False),
            ("Sarah", "Brown", "Anne", "sarah.brown@example.com", "registered", True),
            ("James", "Davis", "", "james.davis@example.com", "rejected", False),
        ]
        for i, (fn, sn, on, em, st, qr) in enumerate(participants, start=1):
            cert_id = generate_certificate_id(fn, sn, i, now)
            u = User(
                first_name=fn, surname=sn, other_name=on, email=em,
                certificate_type_id=ct.id, status=st,
                certificate_id=cert_id if st in ('approved', 'sent') else None,
                include_qr=qr,
                approved_at=now if st == 'approved' else None,
                sent_at=now if st == 'approved' else None,
            )
            db.session.add(u)

            if st == 'approved':
                full_name = f"{fn} {on} {sn}".strip() if on else f"{fn} {sn}"
                db.session.add(CertArchive(
                    certificate_id=cert_id,
                    full_name=full_name,
                    cert_name="Manual Handling Training",
                    issued_date=now.strftime('%d %B %Y'),
                    status='issued'
                ))

        db.session.commit()
        print("✅ 5 sample participants seeded")

    # ── Default Email Draft ────────────────────────────────────────────────
    if EmailDraft.query.count() == 0:
        draft = EmailDraft(
            subject="Your {cert_name} Certificate — Medical Locum Jobs",
            body="""Dear {first_name},

Congratulations on successfully completing {cert_name}!

Please find your personalised certificate attached to this email.

Certificate ID: {cert_id}
Issued: {issued_date}

This certificate has been issued by Medical Locum Jobs as official confirmation of your achievement. Please retain it for your records.

Warm regards,
Medical Locum Jobs Team
https://medicalocumjobs.com""",
            is_default=True
        )
        db.session.add(draft)
        db.session.commit()
        print("✅ Default email draft created")

    print("\n🚀 Setup complete. Login at /login with your ADMIN_EMAIL / ADMIN_PASSWORD.")
