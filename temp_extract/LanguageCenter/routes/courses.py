from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models import Course, User, Enrollment, Student

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')


@courses_bp.route('/')
@login_required
def index():
    # If teacher, show only their courses
    if current_user.role == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.start_date).all()
    else:
        courses = Course.query.order_by(Course.start_date).all()
    
    return render_template('courses/index.html', courses=courses)


@courses_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Only admin can add courses
    if current_user.role != 'admin':
        flash('Bạn không có quyền thêm khóa học.', 'danger')
        return redirect(url_for('courses.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        price = request.form.get('price')
        max_students = request.form.get('max_students')
        total_sessions = request.form.get('total_sessions', 0)
        teacher_id = request.form.get('teacher_id')
        
        # Parse dates
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.', 'danger')
            return redirect(url_for('courses.add'))
        
        # Validate end date is after start date
        if end <= start:
            flash('Ngày kết thúc phải sau ngày bắt đầu.', 'danger')
            return redirect(url_for('courses.add'))
        
        # Convert total_sessions to int
        try:
            total_sessions = int(total_sessions)
        except (ValueError, TypeError):
            total_sessions = 0
            
        # Create new course
        new_course = Course(
            name=name,
            description=description,
            start_date=start,
            end_date=end,
            price=float(price),
            max_students=int(max_students),
            total_sessions=total_sessions,
            active=True
        )
        
        # Add teacher if provided
        if teacher_id:
            new_course.teacher_id = teacher_id
        
        db.session.add(new_course)
        db.session.commit()
        
        flash(f'Khóa học {name} được thêm thành công.', 'success')
        return redirect(url_for('courses.index'))
    
    # Get all teachers for dropdown
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('courses/add.html', teachers=teachers)


@courses_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    course = Course.query.get_or_404(id)
    
    # Check permissions - only admin or the assigned teacher can edit
    if current_user.role != 'admin' and current_user.id != course.teacher_id:
        flash('Bạn không có quyền chỉnh sửa khóa học này.', 'danger')
        return redirect(url_for('courses.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        price = request.form.get('price')
        max_students = request.form.get('max_students')
        total_sessions = request.form.get('total_sessions', 0)
        active = 'active' in request.form
        
        # Only admin can change teacher
        if current_user.role == 'admin':
            teacher_id = request.form.get('teacher_id')
            course.teacher_id = teacher_id if teacher_id else None
        
        # Parse dates
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.', 'danger')
            return redirect(url_for('courses.edit', id=id))
        
        # Validate end date is after start date
        if end <= start:
            flash('Ngày kết thúc phải sau ngày bắt đầu.', 'danger')
            return redirect(url_for('courses.edit', id=id))
        
        # Check if reducing max students below current enrollment
        current_enrollment = len(course.enrollments)
        if int(max_students) < current_enrollment:
            flash(f'Không thể giảm số lượng sinh viên tối đa xuống dưới mức đăng ký hiện tại ({current_enrollment} students).', 'danger')
            return redirect(url_for('courses.edit', id=id))
        
        # Convert total_sessions to int
        try:
            total_sessions = int(total_sessions)
        except (ValueError, TypeError):
            total_sessions = 0
            
        # Update course
        course.name = name
        course.description = description
        course.start_date = start
        course.end_date = end
        course.price = float(price)
        course.max_students = int(max_students)
        course.total_sessions = total_sessions
        course.active = active
        
        db.session.commit()
        
        flash(f'Khóa học {name} được cập nhật thành công.', 'success')
        return redirect(url_for('courses.index'))
    
    # Get all teachers for dropdown
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('courses/edit.html', course=course, teachers=teachers)


@courses_bp.route('/view/<int:id>')
@login_required
def view(id):
    course = Course.query.get_or_404(id)
    
    # Check permissions - only admin or the assigned teacher can view details
    if current_user.role != 'admin' and current_user.id != course.teacher_id:
        flash('Bạn không có quyền xem khóa học này.', 'danger')
        return redirect(url_for('courses.index'))
    
    # Get enrolled students
    enrolled_students = Student.query.join(Enrollment).filter(Enrollment.course_id == id).all()
    
    return render_template('courses/view.html', course=course, students=enrolled_students)


@courses_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    # Only admin can delete courses
    if current_user.role != 'admin':
        flash('Bạn không có quyền xóa khóa học.', 'danger')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(id)
    
    # Check if any students are enrolled
    if course.enrollments:
        flash(f'Không thể xóa khóa học {course.name} bởi vì {len(course.enrollments)} học sinh đã được đăng ký.', 'danger')
        return redirect(url_for('courses.index'))
    
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Khóa học {course.name} được xóa thành công.', 'success')
    return redirect(url_for('courses.index'))


@courses_bp.route('/change-enrollment-status/<int:student_id>/<int:course_id>', methods=['POST'])
@login_required
def change_enrollment_status(student_id, course_id):
    # Only admin or assigned teacher can change status
    course = Course.query.get_or_404(course_id)
    
    if current_user.role != 'admin' and current_user.id != course.teacher_id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('courses.index'))
    
    enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first_or_404()
    new_status = request.form.get('status')
    
    if new_status in ['active', 'completed', 'dropped']:
        enrollment.status = new_status
        db.session.commit()
        
        flash(f'Trạng thái đăng ký đã được cập nhật thành {new_status}.', 'success')
    else:
        flash('Trạng thái không được cung cấp hợp lệ.', 'danger')
    
    return redirect(url_for('courses.view', id=course_id))
