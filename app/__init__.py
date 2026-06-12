import os
from flask import Flask
from flask_login import LoginManager
from app.models import db, User
import cloudinary

login_manager = LoginManager()

def create_app(test_config=None):
    """
    Application Factory for Roadshub platform.
    Initializes configuration, registers database, handles auth session setup,
    and mounts blueprints.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration parameters
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'roadshub-dev-secret-key-12345'),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'DATABASE_URL', 
            'sqlite:///' + os.path.join(app.root_path, 'roadshub.db')
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    # Fix database URL for SQLAlchemy if utilizing newer PostgreSQL URLs (postgres:// vs postgresql://)
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    if db_url.startswith("postgres://"):
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://", 1)
        
    if test_config:
        app.config.from_mapping(test_config)

    # Initialize extensions
    db.init_app(app)
    
    # Flask-Login configuration
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    # Configure Cloudinary for media storage
    # In production, these should be supplied via environment variables
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "roadshub-cloud"),
        api_key=os.environ.get("CLOUDINARY_API_KEY", "mock-api-key"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET", "mock-api-secret"),
        secure=True
    )
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Create tables locally inside the application context if they do not exist
    with app.app_context():
        db.create_all()
        
    return app
