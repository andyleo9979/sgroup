import random
import string
from datetime import datetime
from flask import request, current_app
from flask_login import current_user
from app import db
from models import ActivityLog

def generate_receipt_number():
    """
    Tạo một số biên lai duy nhất cho các khoản thanh toán.
    Định dạng: REC-YYYYMMDD-XXXX trong đó XXXX là một chuỗi         ngẫu nhiên
    """
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"REC-{date_part}-{random_part}"


def format_currency(amount):
    """
    Định dạng một số thành tiền tệ Việt Nam (VND).
    Sử dụng dấu chấm (.) để phân cách hàng nghìn và hiển thị đơn vị VND
    """
    if amount is None:
        return "0 VNĐ"
    # Định dạng số nguyên với dấu phân cách hàng nghìn
    formatted = "{:,.0f}".format(amount)
    # Thay dấu phẩy bằng dấu chấm cho phân cách hàng nghìn theo định dạng tiền Việt Nam
    formatted = formatted.replace(',', '.')
    # Thêm ký hiệu tiền tệ Việt Nam
    return f"{formatted} VNĐ"


def calculate_age(birthdate):
    """
    Tính tuổi dựa theo ngày sinh.
    """
    if not birthdate:
        return None
    
    today = datetime.now().date()
    age = today.year - birthdate.year
    
    # Check if birthday has occurred this year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1
    
    return age


def get_enrollment_status_badge(status):
    """
    Return the appropriate Bootstrap badge class for an enrollment status.
    """
    if status == 'active':
        return 'bg-success'
    elif status == 'completed':
        return 'bg-primary'
    elif status == 'dropped':
        return 'bg-danger'
    else:
        return 'bg-secondary'


def get_notification_type_class(notification_type):
    """
    Return the appropriate Bootstrap alert class for a notification type.
    """
    if notification_type == 'info':
        return 'alert-info'
    elif notification_type == 'warning':
        return 'alert-warning'
    elif notification_type == 'success':
        return 'alert-success'
    elif notification_type == 'error':
        return 'alert-danger'
    else:
        return 'alert-secondary'


def add_log(action, details=None):
    """
    Ghi log hành động của người dùng.
    
    Args:
        action: Tên hành động (ví dụ: "Đăng nhập", "Thêm học sinh", etc.)
        details: Chi tiết về hành động (tùy chọn)
    """
    try:
        # Lấy thông tin về user hiện tại
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Lấy thông tin về IP và trình duyệt
        ip_address = request.remote_addr
        user_agent = request.user_agent.string if request.user_agent else None
        
        # Tạo bản ghi log mới
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Lưu vào database
        db.session.add(log)
        db.session.commit()
        
        return True
    except Exception as e:
        current_app.logger.error(f"Lỗi khi ghi log: {str(e)}")
        return False
