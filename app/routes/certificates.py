from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import db, User, CertificateType, AuditLog
from datetime import datetime
import uuid

bp = Blueprint('certificates', __name__)

@bp.route('/admin')
@login_required
def dashboard():
    cert_types = CertificateType.query.filter_by(is_active=True).all()
    return render_template('admin/dashboard.html', cert_types=cert_types)

@bp.route('/api/users/<int:cert_type_id>')
@login_required
def get_users(cert_type_id):
    users = User.query.filter_by(certificate_type_id=cert_type_id).order_by(User.created_at.desc()).all()
    return jsonify({'data': [{
        'id': u.id,
        'full_name': f"{u.surname} {u.first_name} {u.other_name or ''}".strip(),
        'email': u.email,
        'certificate_id': u.certificate_id or '—',
        'status': u.status,
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else ''
    } for u in users]})

@bp.route('/api/approve', methods=['POST'])
@login_required
def approve_users():
    user_ids = request.json['user_ids']
    User.query.filter(User.id.in_(user_ids)).update({
        'status': 'approved', 'approved_at': datetime.utcnow()
    }, synchronize_session=False)
    for uid in user_ids:
        db.session.add(AuditLog(user_id=uid, action='approved', performed_by=current_user.email))
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} users approved'})

@bp.route('/api/reject', methods=['POST'])
@login_required
def reject_users():
    user_ids = request.json['user_ids']
    User.query.filter(User.id.in_(user_ids)).update({'status': 'rejected'}, synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} users rejected'})

@bp.route('/api/send', methods=['POST'])
@login_required
def send_certificates():
    user_ids = request.json['user_ids']
    cert_type_id = request.json['cert_type_id']
    
    users = User.query.filter(User.id.in_(user_ids), User.status == 'approved').all()
    job_ids = []
    
    for user in users:
        if not user.certificate_id:
            user.certificate_id = str(uuid.uuid4())[:12].upper()
        user.status = 'sent'
        user.sent_at = datetime.utcnow()
        
        job = current_app.task_queue.enqueue(
            'app.worker.generate_and_send_certificate',
            user_id=user.id,
            certificate_type_id=cert_type_id,
            job_timeout=120
        )
        job_ids.append(job.id)
    
    db.session.commit()
    return jsonify({'message': f'{len(job_ids)} certificates queued', 'job_ids': job_ids})

@bp.route('/api/send-all-approved', methods=['POST'])
@login_required
def send_all_approved():
    cert_type_id = request.json['cert_type_id']
    users = User.query.filter_by(certificate_type_id=cert_type_id, status='approved').all()
    user_ids = [u.id for u in users]
    
    if not user_ids:
        return jsonify({'message': 'No approved users found'})
    
    for user in users:
        if not user.certificate_id:
            user.certificate_id = str(uuid.uuid4())[:12].upper()
        user.status = 'sent'
        user.sent_at = datetime.utcnow()
        
        current_app.task_queue.enqueue(
            'app.worker.generate_and_send_certificate',
            user_id=user.id,
            certificate_type_id=cert_type_id,
            job_timeout=120
        )
    
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} certificates queued'})

@bp.route('/api/nudge', methods=['POST'])
@login_required
def nudge_user():
    user_id = request.json['user_id']
    current_app.task_queue.enqueue('app.worker.send_nudge_email', user_id=user_id, job_timeout=30)
    return jsonify({'message': 'Nudge queued'})

@bp.route('/api/delete', methods=['POST'])
@login_required
def delete_users():
    user_ids = request.json['user_ids']
    User.query.filter(User.id.in_(user_ids)).delete()
    db.session.commit()
    return jsonify({'message': f'{len(user_ids)} users deleted'})
