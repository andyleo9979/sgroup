from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from models import User
from utils.helpers import add_log

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Vui lòng kiểm tra thông tin đăng nhập của bạn và thử lại.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        
        # Log đăng nhập
        add_log('Đăng nhập', f'Người dùng {user.username} đăng nhập vào hệ thống')
        
        next_page = request.args.get('next')
        
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
            
        flash(f'Chào mừng trở lại, {user.first_name}!', 'success')
        return redirect(next_page)
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    # Log đăng xuất trước khi xóa thông tin người dùng
    username = current_user.username
    add_log('Đăng xuất', f'Người dùng {username} đăng xuất khỏi hệ thống')
    
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate email uniqueness
        user_with_email = User.query.filter_by(email=email).first()
        if user_with_email and user_with_email.id != current_user.id:
            flash('Email đã được một tài khoản khác sử dụng.', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Update basic info
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email
        
        # Handle password change
        password_changed = False
        if current_password and new_password and confirm_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Mật khẩu hiện tại không chính xác.', 'danger')
                return redirect(url_for('auth.profile'))
            
            if new_password != confirm_password:
                flash('Mật khẩu mới không khớp.', 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.password_hash = generate_password_hash(new_password)
            password_changed = True
            flash('Đã cập nhật mật khẩu thành công.', 'success')
        
        db.session.commit()
        
        # Ghi log cập nhật hồ sơ
        log_details = f'Người dùng {current_user.username} đã cập nhật thông tin hồ sơ cá nhân'
        if password_changed:
            log_details += ', bao gồm thay đổi mật khẩu'
        add_log('Cập nhật hồ sơ', log_details)
        
        flash('Hồ sơ được cập nhật thành công.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('profile.html', user=current_user)


@auth_bp.route('/users')
@login_required
def users():
    # Only admins can access user management
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    users = User.query.all()
    return render_template('users.html', users=users)


@auth_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    # Only admins can add users
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Check if a specific role and return URL were provided
    default_role = request.args.get('role', 'teacher')
    return_to = request.args.get('returnTo')
    course_id = request.args.get('courseId')
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if user already exists
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('Tên người dùng hoặc email đã tồn tại.', 'danger')
            return redirect(url_for('auth.add_user'))
        
        if password != confirm_password:
            flash('Mật khẩu không khớp.', 'danger')
            return redirect(url_for('auth.add_user'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Thêm người dùng', f'Đã thêm người dùng mới: {username}, vai trò: {role}')
        
        flash(f'Người dùng: {username} đã được tạo thành công.', 'success')
        
        # Handle return to specific page if provided
        if return_to:
            if return_to == 'courses.add':
                return redirect(url_for('courses.add'))
            elif return_to == 'courses.edit' and course_id:
                return redirect(url_for('courses.edit', id=course_id))
        
        return redirect(url_for('auth.users'))
    
    return render_template('add_user.html', default_role=default_role)


@auth_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    # Only admins can edit users
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        new_password = request.form.get('new_password')
        
        # Validate email uniqueness
        user_with_email = User.query.filter_by(email=email).first()
        if user_with_email and user_with_email.id != id:
            flash('Email đã được một tài khoản khác sử dụng.', 'danger')
            return redirect(url_for('auth.edit_user', id=id))
        
        # Update user
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        
        # Update password if provided
        password_changed = False
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            password_changed = True
        
        db.session.commit()
        
        # Ghi log hoạt động
        log_details = f'Đã cập nhật thông tin người dùng: {user.username}' 
        if password_changed:
            log_details += ', bao gồm thay đổi mật khẩu'
        add_log('Cập nhật người dùng', log_details)
        
        flash(f'Người dùng: {user.username} đã được cập nhật thành công.', 'success')
        return redirect(url_for('auth.users'))
    
    return render_template('edit_user.html', user=user)


@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    # Only admins can delete users
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Cannot delete own account
    if id == current_user.id:
        flash('Bạn không thể xóa tài khoản của chính mình.', 'danger')
        return redirect(url_for('auth.users'))
    
    user = User.query.get_or_404(id)
    
    # Check if user has courses
    if user.courses:
        flash(f'Không thể xóa người dùng {user.username} vì họ đã được gán vào các khóa học.', 'danger')
        return redirect(url_for('auth.users'))
    
    # Kiểm tra các ràng buộc
    from models import TeacherSalary, TeacherAttendance, TeacherClassSession, Notification
    
    # Đếm số bản ghi liên quan
    salary_count = TeacherSalary.query.filter_by(teacher_id=id).count()
    attendance_count = TeacherAttendance.query.filter_by(teacher_id=id).count()
    sessions_count = TeacherClassSession.query.filter_by(teacher_id=id).count()
    
    # Hiển thị thông báo nếu tồn tại các bản ghi liên quan
    if salary_count > 0 or attendance_count > 0 or sessions_count > 0:
        message = f'Không thể xóa người dùng {user.username} vì tồn tại bản ghi liên quan.<br>'
        if salary_count > 0:
            message += f'- Có {salary_count} bản ghi lương.<br>'
        if attendance_count > 0:
            message += f'- Có {attendance_count} bản ghi điểm danh.<br>'
        if sessions_count > 0:
            message += f'- Có {sessions_count} bản ghi buổi dạy.<br>'
        message += 'Vui lòng xóa các bản ghi này trước khi xóa người dùng.'
        
        flash(message, 'danger')
        return redirect(url_for('auth.users'))
    
    try:
        # Xóa các thông báo và cập nhật các bản ghi liên quan
        # 1. Xóa thông báo
        Notification.query.filter_by(recipient_id=id).delete()
        
        # 2. Cập nhật điểm danh do giáo viên này ghi
        from models import Attendance
        Attendance.query.filter_by(recorded_by=id).update({
            'recorded_by': None
        })
        
        # 3. Cập nhật điểm danh giáo viên do giáo viên này ghi
        TeacherAttendance.query.filter_by(recorded_by=id).update({
            'recorded_by': None
        })
        
        # 4. Xóa người dùng
        db.session.delete(user)
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Xóa người dùng', f'Đã xóa người dùng: {user.username} (ID: {id})')
        
        flash(f'Người dùng: {user.username} đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa người dùng: {str(e)}', 'danger')
    
    return redirect(url_for('auth.users'))


@auth_bp.before_app_request
def get_current_user():
    g.is_admin = current_user.is_authenticated and current_user.role == 'admin'
