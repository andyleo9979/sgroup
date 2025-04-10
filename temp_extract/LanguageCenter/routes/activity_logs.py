from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from models import ActivityLog, User

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/logs')
@login_required
def index():
    """Hiển thị danh sách logs hoạt động"""
    # Chỉ admin mới được xem logs
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy tham số từ URL
    page = request.args.get('page', 1, type=int)
    per_page = 50
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    
    # Query logs với bộ lọc
    query = ActivityLog.query.order_by(desc(ActivityLog.timestamp))
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if action:
        query = query.filter(ActivityLog.action.like(f'%{action}%'))
    
    # Phân trang
    logs = query.paginate(page=page, per_page=per_page)
    
    # Lấy danh sách người dùng để hiển thị dropdown
    users = User.query.all()
    
    # Lấy danh sách các loại hành động duy nhất
    actions = db.session.query(ActivityLog.action.distinct()).all()
    actions = [action[0] for action in actions]
    
    return render_template(
        'activity_logs/index.html', 
        logs=logs, 
        users=users, 
        actions=actions,
        current_user_id=user_id,
        current_action=action
    )


@logs_bp.route('/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    """Xóa tất cả logs"""
    # Chỉ admin mới được xóa logs
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        # Ghi log việc xóa logs
        from utils.helpers import add_log
        add_log('Xóa logs', 'Admin đã xóa tất cả logs hoạt động')
        
        # Xóa tất cả logs trừ log vừa tạo
        db.session.query(ActivityLog).filter(
            ActivityLog.action != 'Xóa logs'
        ).delete()
        db.session.commit()
        
        flash('Đã xóa tất cả logs hoạt động.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa logs: {str(e)}', 'danger')
    
    return redirect(url_for('logs.index'))