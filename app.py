import os
import datetime
import logging
from flask import Flask, flash, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///training_center.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'traning-center@example.com')

# Initialize Flask extensions
db.init_app(app)
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Register blueprints
from routes.messages import messages_bp
app.register_blueprint(messages_bp)

@app.before_request
def before_request():
    g.year = datetime.datetime.now().year
    if current_user.is_authenticated:
        g.is_admin = current_user.role == 'admin'
        g.is_teacher = current_user.role == 'teacher'
    else:
        g.is_admin = False
        g.is_teacher = False

# Đăng ký bộ lọc để định dạng tiền tệ
@app.template_filter('format_currency')
def format_currency_filter(amount):
    from utils.helpers import format_currency
    return format_currency(amount)

# Import and register blueprints
with app.app_context():
    # Import models to create tables
    from models import User, Student, Course, Enrollment, Payment, Notification, Attendance, ActivityLog

    # Create database tables
    db.create_all()

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.students import students_bp
    from routes.courses import courses_bp
    from routes.payments import payments_bp
    from routes.dashboard import dashboard_bp
    from routes.notifications import notifications_bp
    from routes.attendance import attendance_bp
    from routes.import_data import import_bp
    from routes.teacher_attendance import teacher_attendance_bp
    from routes.teacher_salary import teacher_salary_bp
    from routes.activity_logs import logs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(import_bp, url_prefix='/import')
    app.register_blueprint(teacher_attendance_bp, url_prefix='/teacher-attendance')
    app.register_blueprint(teacher_salary_bp, url_prefix='/teacher-salary')
    app.register_blueprint(logs_bp)

    # Create default users if they don't exist
    from werkzeug.security import generate_password_hash
    
    # Kiểm tra người dùng đã có trong db chưa trước khi tạo mới
    with app.app_context():
        # Create sadmin user if none exists
        sadmin = User.query.filter_by(username='sadmin').first()
        if not sadmin:
            sadmin = User(
                username='sadmin',
                email='sadmin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='sadmin',
                first_name='Super',
                last_name='Admin'
            )
            db.session.add(sadmin)
            print("Đã tạo người dùng sadmin")
            
        # Create admin user if none exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                first_name='Admin',
                last_name='User'
            )
            db.session.add(admin)
            print("Đã tạo người dùng admin")
            
        # Create teacher user if none exists
        teacher = User.query.filter_by(username='teacher').first()
        if not teacher:
            teacher = User(
                username='teacher',
                email='teacher@example.com',
                password_hash=generate_password_hash('teacher123'),
                role='teacher',
                first_name='Teacher',
                last_name='User'
            )
            db.session.add(teacher)
            print("Đã tạo người dùng teacher")
            
        try:
            db.session.commit()
        except Exception as e:
            print(f"Lỗi khi tạo người dùng mặc định: {e}")
            db.session.rollback()

    from utils.notification_scheduler import init_scheduler
    # Initialize scheduler after db is created
    init_scheduler(db)  # Pass db instance to scheduler