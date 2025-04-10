from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import Notification, User
from utils.email import send_notification_email

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
@login_required
def index():
    notifications = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/index.html', notifications=notifications)


@notifications_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    # Only admin can send notifications
    if current_user.role != 'admin':
        flash('Bạn không có quyền gửi thông báo.', 'danger')
        return redirect(url_for('notifications.index'))
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        title = request.form.get('title')
        message = request.form.get('message')
        notification_type = request.form.get('notification_type', 'info')
        
        if not recipient_id or not title or not message:
            flash('Tất cả các trường là bắt buộc.', 'danger')
            return redirect(url_for('notifications.create'))
        
        # Handle sending to all users of a role
        if recipient_id == 'all_teachers':
            teachers = User.query.filter_by(role='teacher').all()
            notifications_sent = 0
            
            for teacher in teachers:
                notification = Notification(
                    recipient_id=teacher.id,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
                db.session.add(notification)
                
                # Also attempt to send email
                try:
                    send_notification_email(teacher.email, title, message)
                except Exception as e:
                    flash(f'Cảnh báo: Không thể gửi email đến {teacher.email}: {str(e)}', 'warning')
                
                notifications_sent += 1
            
            db.session.commit()
            flash(f'Thông báo được gửi tới {notifications_sent} teachers.', 'success')
            return redirect(url_for('notifications.index'))
        else:
            # Send to a specific user
            user = User.query.get(recipient_id)
            if not user:
                flash('Không tìm thấy người nhận.', 'danger')
                return redirect(url_for('notifications.create'))
            
            notification = Notification(
                recipient_id=recipient_id,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Also attempt to send email
            try:
                send_notification_email(user.email, title, message)
            except Exception as e:
                flash(f'Thông báo đã được lưu nhưng không thể gửi email: {str(e)}', 'warning')
                return redirect(url_for('notifications.index'))
            
            flash('Thông báo đã được gửi thành công.', 'success')
            return redirect(url_for('notifications.index'))
    
    # Get all users for the dropdown
    users = User.query.all()
    return render_template('notifications/create.html', users=users)


@notifications_bp.route('/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_read(id):
    notification = Notification.query.get_or_404(id)
    
    # Check if current user is the recipient
    if notification.recipient_id != current_user.id:
        flash('Bạn không có quyền sửa đổi thông báo này.', 'danger')
        return redirect(url_for('notifications.index'))
    
    notification.is_read = True
    db.session.commit()
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Thông báo được đánh dấu là đã đọc.', 'success')
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    notifications = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).all()
    
    for notification in notifications:
        notification.is_read = True
    
    db.session.commit()
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'count': len(notifications)})
    
    flash('Tất cả thông báo được đánh dấu là đã đọc.', 'success')
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    notification = Notification.query.get_or_404(id)
    
    # Check if current user is the recipient or an admin
    if notification.recipient_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền xóa thông báo này.', 'danger')
        return redirect(url_for('notifications.index'))
    
    db.session.delete(notification)
    db.session.commit()
    
    flash('Đã xóa thông báo.', 'success')
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/count')
@login_required
def count():
    # Count unread notifications for current user
    unread_count = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    
    # Return JSON for AJAX requests
    return jsonify({'count': unread_count})
