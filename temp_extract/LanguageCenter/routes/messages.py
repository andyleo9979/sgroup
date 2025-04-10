
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import Message, User
from sqlalchemy import or_

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')

@messages_bp.route('/')
@login_required
def index():
    """Hiển thị trang tin nhắn"""
    messages = Message.query.filter(
        or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).order_by(Message.created_at.desc()).all()
    
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('messages/index.html', messages=messages, users=users)

@messages_bp.route('/send', methods=['POST'])
@login_required
def send():
    """Gửi tin nhắn mới"""
    recipient_id = request.form.get('recipient_id')
    content = request.form.get('content')
    
    if not recipient_id or not content:
        flash('Vui lòng điền đầy đủ thông tin.', 'danger')
        return redirect(url_for('messages.index'))
    
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': {
            'id': message.id,
            'content': message.content,
            'sender_name': message.sender.full_name,
            'created_at': message.created_at.strftime('%H:%M %d-%m-%Y')
        }
    })

@messages_bp.route('/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_read(id):
    """Đánh dấu tin nhắn đã đọc"""
    message = Message.query.get_or_404(id)
    
    if message.recipient_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Không có quyền truy cập'}), 403
    
    message.is_read = True
    db.session.commit()
    
    return jsonify({'status': 'success'})
