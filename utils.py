from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from flask_mail import Message
from app import mail

def requires_roles(roles):
    """Decorator that checks if the current user has one of the required roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('Bạn không có quyền truy cập trang này.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_assessment_email(student, assessment, teacher):
    """Send an assessment email to a student."""
    try:
        subject = f"Đánh giá học tập từ trung tâm SGROUP - {assessment.date.strftime('%d/%m/%Y')}"
        
        msg = Message(
            subject=subject,
            recipients=[student.email]
        )
        
        msg.body = f"""
Xin chào {student.full_name},

Giáo viên {teacher.full_name} đã đánh giá kết quả học tập của bạn vào ngày {assessment.date.strftime('%d/%m/%Y')}:

{assessment.content}

Trân trọng,
Trung tâm đào tạo SGROUP
        """
        
        # Format the content with line breaks first
        content_html = assessment.content.replace('\n', '<br>')
        
        msg.html = f"""
<p>Xin chào <strong>{student.full_name}</strong>,</p>

<p>Giáo viên <strong>{teacher.full_name}</strong> đã đánh giá kết quả học tập của bạn vào ngày <strong>{assessment.date.strftime('%d/%m/%Y')}</strong>:</p>

<blockquote style="border-left: 3px solid #ccc; padding-left: 10px; margin-left: 10px;">
    {content_html}
</blockquote>

<p>Trân trọng,<br>
Trung tâm đào tạo SGROUP</p>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def format_currency(value):
    """Format a number as currency (VND)."""
    if value is None:
        return "0 ₫"
    return f"{int(value):,} ₫".replace(',', '.')

def format_date(date_obj):
    """Format a date in Vietnamese format."""
    if date_obj is None:
        return ""
    return date_obj.strftime('%d/%m/%Y')
