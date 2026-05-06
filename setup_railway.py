"""Run once on Railway to create admin and sample data."""
from app import create_app, db
from app.models import Admin, CertificateType
import uuid
import os

app = create_app()

with app.app_context():
    db.create_all()
    
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@medicalocumjobs.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123')
    
    if not Admin.query.filter_by(email=admin_email).first():
        admin = Admin(email=admin_email)
        admin.set_password(admin_password)
        db.session.add(admin)
        print(f"Admin created: {admin_email}")
    
    if CertificateType.query.count() == 0:
        token = str(uuid.uuid4())[:8]
        cert = CertificateType(
            name="Sample Certificate",
            period="March 2026",
            master_pdf_path="uploads/sample_master.pdf",
            overlay_coords={
                "name_x": 300, "name_y": 400,
                "cert_id_x": 50, "cert_id_y": 50,
                "qr_x": 450, "qr_y": 50,
                "date_x": 50, "date_y": 30
            },
            registration_token=token,
            is_active=True
        )
        db.session.add(cert)
        db.session.commit()
        print(f"Sample cert created. Register: /register/{token}")
    
    print("Setup complete.")
