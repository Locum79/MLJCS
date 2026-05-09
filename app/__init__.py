from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, static_folder='../static')
    app.config.from_object('app.config.Config')

    db.init_app(app)
    
    os.makedirs(os.path.join(app.root_path, '../uploads'), exist_ok=True)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)


    from app.routes import auth, registration, certificates
    from app.routes import email_routes
    app.register_blueprint(auth.bp)
    app.register_blueprint(registration.bp)
    app.register_blueprint(certificates.bp)
    app.register_blueprint(email_routes.bp)

    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

    return app


from app.models import Admin


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))
