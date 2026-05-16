from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from app.utils.tasks import task_queue
import os
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()


def create_app():
    app = Flask(__name__, static_folder='../static')
    app.config.from_object('app.config.Config')
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    mail.init_app(app)
    task_queue.init_app(app)
    from app.utils.paths import ensure_upload_root
    ensure_upload_root()
    from app.routes import auth, registration, certificates
    from app.routes import email_routes
    app.register_blueprint(auth.bp)
    app.register_blueprint(registration.bp)
    app.register_blueprint(certificates.bp)
    app.register_blueprint(email_routes.bp)
    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import Admin
    return Admin.query.get(int(user_id))
