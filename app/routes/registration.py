from flask import Blueprint, request, render_template, jsonify
from app.models import db, User, CertificateType

bp = Blueprint('registration', __name__)

@bp.route('/register/<token>', methods=['GET'])
def registration_form(token):
    cert_type = CertificateType.query.filter_by(registration_token=token, is_active=True).first_or_404()
    return render_template('public/register.html', cert_type=cert_type)

@bp.route('/register/<token>', methods=['POST'])
def submit_registration(token):
    cert_type = CertificateType.query.filter_by(registration_token=token, is_active=True).first_or_404()
    
    user = User(
        first_name=request.form['first_name'],
        surname=request.form['surname'],
        other_name=request.form.get('other_name', ''),
        email=request.form['email'],
        certificate_type_id=cert_type.id,
        status='registered'
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Registration successful'})
