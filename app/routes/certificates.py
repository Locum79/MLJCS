from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models import db, User, CertificateType, AuditLog, CertArchive, EmailDraft
from app.engine.luhn import verify_certificate_id
from datetime import datetime
import uuid
import os
import json

bp = Blueprint('certificates', __name__)

UPLOAD_FOLDER = 'uploads'


# ── Dashboard ────────────────────────────────────────────────────────────────

@bp.route('/admin')
@login_required
def dashboard():
    cert_types = CertificateType.query.filter_by(is_active=True).order_by(CertificateType.created_at.desc()).all()
    drafts = EmailDraft.query.order_by(EmailDraft.updated_at.desc()).all()
    return render_template('admin/dashboard.html', cert_types=cert_types, drafts=drafts)


# ── Certificate Library (master upload) ─────────────────────────────────────

@bp.route('/api/cert-types', methods=['GET'])
@login_required
def list_cert_types():
    types = CertificateType.query.filter_by(is_active=True).order_by(CertificateType.created_at.desc()).all()
    return jsonify([{
        'id': ct.id,
        'name': ct.name,
        'period': ct.period,
        'registration_token': ct.registration_token,
        'master_file_type': ct.master_file_type,
        'user_count': len(ct.users)
    } for ct in types])


@bp.route('/api/cert-types', methods=['POST'])
@login_required
def create_cert_type():
    file = request.files.get('master_file')
    if not file:
        return jsonify({'error': 'Master file required'}), 400

    name = request.form.get('name', '').strip()
    period = request.form.get('period', '').strip()
    if not name or not period:
        return jsonify({'error': 'Name and period required'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('pdf', 'png'):
        return jsonify({'error': 'Only PDF or PNG allowed'}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Default overlay coords — admin can customise later
    overlay_coords = {
        "name_x": 0, "name_y": 380,
        "name_font_size": 28,
        "cert_id_x": 50, "cert_id_y": 52,
        "date_x": 50, "date_y": 38,
        "qr_x": -1, "qr_y": 30,
        "qr_size": 90
    }

    try:
        overlay_coords = json.loads(request.form.get('overlay_coords', 'null') or 'null') or overlay_coords
    except Exception:
        pass

    token = str(uuid.uuid4())[:8]
    email_message = request.form.get('email_message', '').strip() or None

    ct = CertificateType(
        name=name,
        period=period,
        master_pdf_path=filepath,
        master_file_type=ext,
        overlay_coords=overlay_coords,
        registration_token=token,
        email_message=email_message
    )
    db.session.add(ct)
    db.session.commit()

    return jsonify({
        'id': ct.id,
        'name': ct.name,
        'registration_token': token,
        'register_url': f"/register/{token}"
    })


@bp.route('/api/cert-types/<int:ct_id>', methods=['PUT'])
@login_required
def update_cert_type(ct_id):
    ct = CertificateType.query.get_or_404(ct_id)
    data = request.json or {}
    if 'name' in data:
        ct.name = data['name']
    if 'period' in data:
        ct.period = data['period']
    if 'overlay_coords' in data:
        ct.overlay_coords = data['overlay_coords']
    if 'email_message' in data:
        ct.email_message = data['email_message']
    db.session.commit()
    return jsonify({'message': 'Updated'})


@bp.route('/api/cert-types/<int:ct_id>', methods=['DELETE'])
@login_required
def delete_cert_type(ct_id):
    ct = CertificateType.query.get_or_404(ct_id)
    ct.is_active = False
    db.session.commit()
    return jsonify({'message': 'Removed from library'})


# ── Users ────────────────────────────────────────────────────────────────────

@bp.route('/api/users/<int:cert_type_id>')
@login_required
def get_users(cert_type_id):
    users = User.query.filter_by(certificate_type_id=cert_type_id).order_by(User.created_at.desc()).all()
    return jsonify({'data': [{
        'id': u.id,
        'full_name': u.full_name,
        'email': u.email,
        'certificate_id': u.certificate_id or '—',
        'status': u.status,
        'include_qr': u.include_qr,
        'created_at': u.created_at.strftime('%d/%m/%Y %H:%M') if u.created_at else ''
    } for u in users]})


@bp.route('/api/users/add', methods=['POST'])
@login_required
def add_user():
    data = request.json or {}
    user = User(
        first_name=data.get('first_name', '').strip(),
        surname=data.get('surname', '').strip(),
        other_name=data.get('other_name', '').strip(),
        email=data.get('email', '').strip().lower(),
        certificate_type_id=data['cert_type_id'],
        status='registered'
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Participant added', 'id': user.id})


@bp.route('/api/users/toggle-qr', methods=['POST'])
@login_required
def toggle_qr():
    user_id = request.json.get('user_id')
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    user.include_qr = not user.include_qr
    db.session.commit()
    return jsonify({'include_qr': user.include_qr})


@bp.route('/api/approve', methods=['POST'])
@login_required
def approve_users():
    user_ids = request.json['user_ids']
    User.query.filter(User.id.in_(user_ids)).update(
        {'status': 'approved', 'approved_at': datetime.utcnow()},
        synchronize_session=False
    )
    for uid in user_ids:
        db.session.add(AuditLog(user_id=uid, action='approved', performed_by=current_user.email))
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} approved'})


@bp.route('/api/reject', methods=['POST'])
@login_required
def reject_users():
    user_ids = request.json['user_ids']
    User.query.filter(User.id.in_(user_ids)).update({'status': 'rejected'}, synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} rejected'})


@bp.route('/api/send', methods=['POST'])
@login_required
def send_certificates():
    user_ids = request.json['user_ids']
    cert_type_id = request.json['cert_type_id']
    draft_id = request.json.get('draft_id')

    # Attach custom draft to cert type temporarily if chosen
    if draft_id:
        draft = db.session.get(EmailDraft, draft_id)
        if draft:
            ct = db.session.get(CertificateType, cert_type_id)
            ct.email_message = draft.body
            db.session.flush()

    users = User.query.filter(User.id.in_(user_ids), User.status == 'approved').all()
    queued = 0
    for user in users:
        user.status = 'sending'
        user.sent_at = datetime.utcnow()
        current_app.task_queue.enqueue(
            'app.worker.generate_and_send_certificate',
            user_id=user.id,
            certificate_type_id=cert_type_id,
            job_timeout=180
        )
        queued += 1

    db.session.commit()
    return jsonify({'message': f'{queued} certificates queued'})


@bp.route('/api/send-all-approved', methods=['POST'])
@login_required
def send_all_approved():
    cert_type_id = request.json['cert_type_id']
    draft_id = request.json.get('draft_id')

    if draft_id:
        draft = db.session.get(EmailDraft, draft_id)
        if draft:
            ct = db.session.get(CertificateType, cert_type_id)
            ct.email_message = draft.body
            db.session.flush()

    users = User.query.filter_by(certificate_type_id=cert_type_id, status='approved').all()
    if not users:
        return jsonify({'message': 'No approved participants found'})

    for user in users:
        user.status = 'sending'
        user.sent_at = datetime.utcnow()
        current_app.task_queue.enqueue(
            'app.worker.generate_and_send_certificate',
            user_id=user.id,
            certificate_type_id=cert_type_id,
            job_timeout=180
        )

    db.session.commit()
    return jsonify({'message': f'{len(users)} certificates queued'})


@bp.route('/api/nudge', methods=['POST'])
@login_required
def nudge_user():
    user_id = request.json['user_id']
    current_app.task_queue.enqueue('app.worker.send_nudge_email', user_id=user_id, job_timeout=30)
    return jsonify({'message': 'Reminder sent'})


@bp.route('/api/delete', methods=['POST'])
@login_required
def delete_users():
    user_ids = request.json['user_ids']
    # Archive cert IDs before deletion
    users = User.query.filter(User.id.in_(user_ids)).all()
    for u in users:
        if u.certificate_id:
            existing = CertArchive.query.filter_by(certificate_id=u.certificate_id).first()
            if not existing:
                db.session.add(CertArchive(
                    certificate_id=u.certificate_id,
                    full_name=u.full_name,
                    cert_name=u.certificate_type.name if u.certificate_type else '',
                    issued_date=u.sent_at.strftime('%d %B %Y') if u.sent_at else '',
                    status='archived',
                    raw_binary=json.dumps({'email': u.email}).encode('utf-8')
                ))
    User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} participants deleted'})


# ── Email Drafts ─────────────────────────────────────────────────────────────

@bp.route('/api/drafts', methods=['GET'])
@login_required
def list_drafts():
    drafts = EmailDraft.query.order_by(EmailDraft.updated_at.desc()).all()
    return jsonify([{
        'id': d.id,
        'subject': d.subject,
        'body': d.body,
        'is_default': d.is_default,
        'updated_at': d.updated_at.strftime('%d/%m/%Y') if d.updated_at else ''
    } for d in drafts])


@bp.route('/api/drafts', methods=['POST'])
@login_required
def save_draft():
    data = request.json or {}
    draft = EmailDraft(
        subject=data.get('subject', 'Your {cert_name} Certificate — MLJ'),
        body=data.get('body', ''),
        is_default=data.get('is_default', False)
    )
    db.session.add(draft)
    db.session.commit()
    return jsonify({'id': draft.id, 'message': 'Draft saved'})


@bp.route('/api/drafts/<int:draft_id>', methods=['PUT'])
@login_required
def update_draft(draft_id):
    draft = db.session.get(EmailDraft, draft_id)
    if not draft:
        return jsonify({'error': 'Not found'}), 404
    data = request.json or {}
    draft.subject = data.get('subject', draft.subject)
    draft.body = data.get('body', draft.body)
    draft.is_default = data.get('is_default', draft.is_default)
    draft.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Draft updated'})


@bp.route('/api/drafts/<int:draft_id>', methods=['DELETE'])
@login_required
def delete_draft(draft_id):
    draft = db.session.get(EmailDraft, draft_id)
    if not draft:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(draft)
    db.session.commit()
    return jsonify({'message': 'Draft deleted'})


# ── QR Verification (public) ─────────────────────────────────────────────────

@bp.route('/verify/<cert_id>')
def verify_cert(cert_id):
    record = CertArchive.query.filter_by(certificate_id=cert_id).first()
    if not record:
        # Try active users
        user = User.query.filter_by(certificate_id=cert_id).first()
        if user:
            record = type('R', (), {
                'certificate_id': user.certificate_id,
                'full_name': user.full_name,
                'cert_name': user.certificate_type.name if user.certificate_type else '',
                'issued_date': user.sent_at.strftime('%d %B %Y') if user.sent_at else '',
                'status': user.status
            })()

    luhn_valid = verify_certificate_id(cert_id)
    return render_template('public/verify.html', record=record, luhn_valid=luhn_valid, cert_id=cert_id)


# ── Archive lookup ────────────────────────────────────────────────────────────

@bp.route('/api/archive/<cert_id>')
@login_required
def get_archive(cert_id):
    record = CertArchive.query.filter_by(certificate_id=cert_id).first()
    if not record:
        return jsonify({'error': 'Not found'}), 404
    data = record.to_dict()
    if record.raw_binary:
        try:
            data['raw'] = json.loads(record.raw_binary.decode('utf-8'))
        except Exception:
            pass
    return jsonify(data)
