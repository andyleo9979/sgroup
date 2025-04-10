from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, extract
from datetime import datetime, date, timedelta
import calendar
from app import app, db, mail
from models import User, Student, Course, Enrollment, StudentAttendance, TeacherAttendance, TeacherSalary, Assessment, Message
from forms import (
    LoginForm, CourseForm, UserForm, StudentForm, EnrollmentForm,
    StudentAttendanceForm, TeacherAttendanceForm, TeacherSalaryForm,
    AssessmentForm, MessageForm, SearchForm
)
from flask_mail import Message as MailMessage
import json
from utils import requires_roles, send_assessment_email

# Dashboard route
@app.route('/')
@login_required
def dashboard():
    # Count active courses
    active_courses_count = Course.query.filter_by(active=True).count()
    
    # Count active students
    active_students_count = Student.query.filter_by(active=True).count()
    
    # Count active teachers
    active_teachers_count = User.query.filter_by(role='teacher', active=True).count()
    
    # Calculate revenue data
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    revenue_data = db.session.query(
        extract('month', Enrollment.payment_date).label('month'),
        func.sum(Enrollment.fee_paid).label('revenue')
    ).filter(
        extract('year', Enrollment.payment_date) == current_year,
        Enrollment.payment_status.in_(['partial', 'paid'])
    ).group_by('month').all()
    
    # Format revenue data for charts
    months = [calendar.month_name[m] for m in range(1, 13)]
    revenue_values = [0] * 12
    
    for month, revenue in revenue_data:
        if month:
            revenue_values[int(month) - 1] = float(revenue)
    
    # Get course enrollment data
    course_data = db.session.query(
        Course.name,
        func.count(Enrollment.id).label('student_count')
    ).join(Enrollment).filter(
        Course.active == True,
        Enrollment.active == True
    ).group_by(Course.name).limit(10).all()
    
    course_names = [course[0] for course in course_data]
    course_students = [course[1] for course in course_data]
    
    # Get unread messages count
    unread_messages_count = Message.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).count()
    
    # Get recent assessments
    recent_assessments = Assessment.query.order_by(
        Assessment.created_at.desc()
    ).limit(5).all()
    
    return render_template(
        'dashboard.html',
        active_courses_count=active_courses_count,
        active_students_count=active_students_count,
        active_teachers_count=active_teachers_count,
        months=json.dumps(months),
        revenue_values=json.dumps(revenue_values),
        course_names=json.dumps(course_names),
        course_students=json.dumps(course_students),
        unread_messages_count=unread_messages_count,
        recent_assessments=recent_assessments
    )

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data) and user.active:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Tên đăng nhập hoặc mật khẩu không chính xác.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất thành công.', 'success')
    return redirect(url_for('login'))

# User management routes
@app.route('/users')
@login_required
@requires_roles(['sadmin', 'admin'])
def users():
    search_form = SearchForm()
    query = User.query
    
    search_term = request.args.get('search', '')
    if search_term:
        query = query.filter(
            (User.username.ilike(f'%{search_term}%')) |
            (User.email.ilike(f'%{search_term}%')) |
            (User.full_name.ilike(f'%{search_term}%'))
        )
    
    role_filter = request.args.get('role', '')
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    users = query.order_by(User.username).all()
    
    return render_template(
        'users.html',
        users=users,
        search_form=search_form,
        search_term=search_term,
        role_filter=role_filter
    )

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Tên đăng nhập đã tồn tại.', 'danger')
            return render_template('user_detail.html', form=form, is_edit=False)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email đã tồn tại.', 'danger')
            return render_template('user_detail.html', form=form, is_edit=False)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            full_name=form.full_name.data,
            phone=form.phone.data,
            role=form.role.data,
            active=form.active.data
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Người dùng đã được tạo thành công.', 'success')
        return redirect(url_for('users'))
    
    return render_template('user_detail.html', form=form, is_edit=False)

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Super admin can edit anyone, admin can only edit teachers and themselves
    if current_user.role != 'sadmin' and (user.role == 'sadmin' or 
                                          (user.role == 'admin' and user.id != current_user.id)):
        flash('Bạn không có quyền chỉnh sửa người dùng này.', 'danger')
        return redirect(url_for('users'))
    
    form = UserForm(obj=user)
    
    # Don't allow changing the role of sadmin users
    if user.role == 'sadmin' and current_user.id != user.id:
        form.role.render_kw = {'disabled': 'disabled'}
    
    if form.validate_on_submit():
        # Check if username or email already exists for other users
        username_exists = User.query.filter(
            User.username == form.username.data,
            User.id != user_id
        ).first()
        
        email_exists = User.query.filter(
            User.email == form.email.data,
            User.id != user_id
        ).first()
        
        if username_exists:
            flash('Tên đăng nhập đã tồn tại.', 'danger')
            return render_template('user_detail.html', form=form, is_edit=True, user=user)
        
        if email_exists:
            flash('Email đã tồn tại.', 'danger')
            return render_template('user_detail.html', form=form, is_edit=True, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.phone = form.phone.data
        
        # Only change role if the user is not a sadmin or if the current user is the sadmin being edited
        if user.role != 'sadmin' or current_user.id == user.id:
            user.role = form.role.data
        
        user.active = form.active.data
        
        # Only update password if provided
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        db.session.commit()
        
        flash('Người dùng đã được cập nhật thành công.', 'success')
        return redirect(url_for('users'))
    
    # Don't display password in edit form
    form.password.data = ''
    
    return render_template('user_detail.html', form=form, is_edit=True, user=user)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Sadmin can delete anyone except themselves
    # Admin can only delete teachers who aren't assigned to active courses
    if current_user.role == 'sadmin':
        if user.id == current_user.id:
            flash('Bạn không thể xóa tài khoản của chính mình.', 'danger')
            return redirect(url_for('users'))
    elif current_user.role == 'admin':
        if user.role == 'sadmin' or user.role == 'admin':
            flash('Bạn không có quyền xóa người dùng này.', 'danger')
            return redirect(url_for('users'))
        
        # Check if teacher is assigned to any active courses
        active_courses = Course.query.filter_by(
            teacher_id=user.id,
            active=True
        ).first()
        
        if active_courses:
            flash('Không thể xóa giáo viên đã được phân công khóa học đang hoạt động.', 'danger')
            return redirect(url_for('users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('Người dùng đã được xóa thành công.', 'success')
    return redirect(url_for('users'))

# Course management routes
@app.route('/courses')
@login_required
def courses():
    search_form = SearchForm()
    query = Course.query
    
    search_term = request.args.get('search', '')
    if search_term:
        query = query.filter(
            (Course.name.ilike(f'%{search_term}%')) |
            (Course.description.ilike(f'%{search_term}%'))
        )
    
    status_filter = request.args.get('status', '')
    if status_filter == 'active':
        query = query.filter_by(active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(active=False)
    
    if current_user.role == 'teacher':
        # Teachers can only see their assigned courses
        query = query.filter_by(teacher_id=current_user.id)
    
    courses = query.order_by(Course.start_date.desc()).all()
    
    return render_template(
        'courses.html',
        courses=courses,
        search_form=search_form,
        search_term=search_term,
        status_filter=status_filter
    )

@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def add_course():
    form = CourseForm()
    
    # Populate teacher choices
    teachers = User.query.filter_by(role='teacher', active=True).all()
    form.teacher_id.choices = [(0, 'Chọn giáo viên')] + [(t.id, t.full_name) for t in teachers]
    
    if form.validate_on_submit():
        course = Course(
            name=form.name.data,
            description=form.description.data,
            teacher_id=form.teacher_id.data if form.teacher_id.data != 0 else None,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            schedule=form.schedule.data,
            max_students=form.max_students.data,
            fee=form.fee.data,
            session_fee=form.session_fee.data,
            active=form.active.data
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash('Khóa học đã được tạo thành công.', 'success')
        return redirect(url_for('courses'))
    
    return render_template('course_detail.html', form=form, is_edit=False)

@app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    form = CourseForm(obj=course)
    
    # Populate teacher choices
    teachers = User.query.filter_by(role='teacher', active=True).all()
    form.teacher_id.choices = [(0, 'Chọn giáo viên')] + [(t.id, t.full_name) for t in teachers]
    
    if form.validate_on_submit():
        course.name = form.name.data
        course.description = form.description.data
        course.teacher_id = form.teacher_id.data if form.teacher_id.data != 0 else None
        course.start_date = form.start_date.data
        course.end_date = form.end_date.data
        course.schedule = form.schedule.data
        course.max_students = form.max_students.data
        course.fee = form.fee.data
        course.session_fee = form.session_fee.data
        course.active = form.active.data
        
        db.session.commit()
        
        flash('Khóa học đã được cập nhật thành công.', 'success')
        return redirect(url_for('courses'))
    
    return render_template('course_detail.html', form=form, is_edit=True, course=course)

@app.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Admin can only delete courses with no students
    if current_user.role == 'admin':
        enrolled_students = Enrollment.query.filter_by(
            course_id=course.id,
            active=True
        ).first()
        
        if enrolled_students:
            flash('Không thể xóa khóa học đã có học sinh đăng ký.', 'danger')
            return redirect(url_for('courses'))
    
    db.session.delete(course)
    db.session.commit()
    
    flash('Khóa học đã được xóa thành công.', 'success')
    return redirect(url_for('courses'))

@app.route('/courses/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course_id, active=True).all()
    
    # Get students for this course
    students = Student.query.join(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.active == True
    ).all()
    
    # Get teacher if assigned
    teacher = User.query.get(course.teacher_id) if course.teacher_id else None
    
    # Calculate total revenue
    total_revenue = db.session.query(func.sum(Enrollment.fee_paid)).filter(
        Enrollment.course_id == course_id,
        Enrollment.active == True
    ).scalar() or 0
    
    # Get student and teacher attendance statistics
    student_attendance_stats = db.session.query(
        StudentAttendance.status,
        func.count(StudentAttendance.id)
    ).filter(
        StudentAttendance.course_id == course_id
    ).group_by(StudentAttendance.status).all()
    
    teacher_attendance_stats = db.session.query(
        TeacherAttendance.status,
        func.count(TeacherAttendance.id)
    ).filter(
        TeacherAttendance.course_id == course_id
    ).group_by(TeacherAttendance.status).all()
    
    return render_template(
        'course_detail.html',
        course=course,
        enrollments=enrollments,
        students=students,
        teacher=teacher,
        total_revenue=total_revenue,
        student_attendance_stats=dict(student_attendance_stats),
        teacher_attendance_stats=dict(teacher_attendance_stats)
    )

# Student management routes
@app.route('/students')
@login_required
def students():
    search_form = SearchForm()
    query = Student.query
    
    search_term = request.args.get('search', '')
    if search_term:
        query = query.filter(
            (Student.full_name.ilike(f'%{search_term}%')) |
            (Student.email.ilike(f'%{search_term}%')) |
            (Student.phone.ilike(f'%{search_term}%'))
        )
    
    status_filter = request.args.get('status', '')
    if status_filter == 'active':
        query = query.filter_by(active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(active=False)
    
    students = query.order_by(Student.full_name).all()
    
    return render_template(
        'students.html',
        students=students,
        search_form=search_form,
        search_term=search_term,
        status_filter=status_filter
    )

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def add_student():
    form = StudentForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        if Student.query.filter_by(email=form.email.data).first():
            flash('Email đã tồn tại.', 'danger')
            return render_template('student_detail.html', form=form, is_edit=False)
        
        student = Student(
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            date_of_birth=form.date_of_birth.data,
            address=form.address.data,
            parent_name=form.parent_name.data,
            parent_phone=form.parent_phone.data,
            active=form.active.data
        )
        
        db.session.add(student)
        db.session.commit()
        
        flash('Học sinh đã được tạo thành công.', 'success')
        return redirect(url_for('students'))
    
    return render_template('student_detail.html', form=form, is_edit=False)

@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)
    
    if form.validate_on_submit():
        # Check if email already exists for other students
        email_exists = Student.query.filter(
            Student.email == form.email.data,
            Student.id != student_id
        ).first()
        
        if email_exists:
            flash('Email đã tồn tại.', 'danger')
            return render_template('student_detail.html', form=form, is_edit=True, student=student)
        
        student.full_name = form.full_name.data
        student.email = form.email.data
        student.phone = form.phone.data
        student.date_of_birth = form.date_of_birth.data
        student.address = form.address.data
        student.parent_name = form.parent_name.data
        student.parent_phone = form.parent_phone.data
        student.active = form.active.data
        
        db.session.commit()
        
        flash('Học sinh đã được cập nhật thành công.', 'success')
        return redirect(url_for('students'))
    
    return render_template('student_detail.html', form=form, is_edit=True, student=student)

@app.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Admin can only delete students not enrolled in active courses
    if current_user.role == 'admin':
        active_enrollments = Enrollment.query.join(Course).filter(
            Enrollment.student_id == student_id,
            Enrollment.active == True,
            Course.active == True
        ).first()
        
        if active_enrollments:
            flash('Không thể xóa học sinh đã đăng ký khóa học đang hoạt động.', 'danger')
            return redirect(url_for('students'))
    
    db.session.delete(student)
    db.session.commit()
    
    flash('Học sinh đã được xóa thành công.', 'success')
    return redirect(url_for('students'))

@app.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Get active enrollments for this student
    enrollments = Enrollment.query.join(Course).filter(
        Enrollment.student_id == student_id,
        Enrollment.active == True
    ).all()
    
    # Get attendance history
    attendance_history = StudentAttendance.query.filter_by(
        student_id=student_id
    ).order_by(StudentAttendance.date.desc()).limit(30).all()
    
    # Get assessment history
    assessment_history = Assessment.query.filter_by(
        student_id=student_id
    ).order_by(Assessment.date.desc()).limit(10).all()
    
    # Calculate attendance statistics
    attendance_stats = db.session.query(
        StudentAttendance.status,
        func.count(StudentAttendance.id)
    ).filter(
        StudentAttendance.student_id == student_id
    ).group_by(StudentAttendance.status).all()
    
    # Calculate total fees paid
    total_fees_paid = db.session.query(func.sum(Enrollment.fee_paid)).filter(
        Enrollment.student_id == student_id
    ).scalar() or 0
    
    return render_template(
        'student_detail.html',
        student=student,
        enrollments=enrollments,
        attendance_history=attendance_history,
        assessment_history=assessment_history,
        attendance_stats=dict(attendance_stats),
        total_fees_paid=total_fees_paid
    )

# Enrollment routes
@app.route('/enrollments/add', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def add_enrollment():
    form = EnrollmentForm()
    
    # Populate student and course choices
    students = Student.query.filter_by(active=True).all()
    form.student_id.choices = [(0, 'Chọn học sinh')] + [(s.id, s.full_name) for s in students]
    
    active_courses = Course.query.filter_by(active=True).all()
    form.course_id.choices = [(0, 'Chọn khóa học')] + [(c.id, c.name) for c in active_courses]
    
    if form.validate_on_submit():
        # Check if student is already enrolled in this course
        existing_enrollment = Enrollment.query.filter_by(
            student_id=form.student_id.data,
            course_id=form.course_id.data,
            active=True
        ).first()
        
        if existing_enrollment:
            flash('Học sinh đã đăng ký khóa học này.', 'danger')
            return render_template('enrollment_form.html', form=form)
        
        # Check if course has reached max students
        course = Course.query.get(form.course_id.data)
        current_enrollments = Enrollment.query.filter_by(
            course_id=form.course_id.data,
            active=True
        ).count()
        
        if current_enrollments >= course.max_students:
            flash('Khóa học đã đạt số lượng học sinh tối đa.', 'danger')
            return render_template('enrollment_form.html', form=form)
        
        enrollment = Enrollment(
            student_id=form.student_id.data,
            course_id=form.course_id.data,
            enrollment_date=form.enrollment_date.data or date.today(),
            fee_paid=form.fee_paid.data,
            payment_status=form.payment_status.data,
            payment_date=form.payment_date.data,
            active=True
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Đăng ký khóa học thành công.', 'success')
        return redirect(url_for('course_detail', course_id=form.course_id.data))
    
    return render_template('enrollment_form.html', form=form)

@app.route('/enrollments/<int:enrollment_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def edit_enrollment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    form = EnrollmentForm(obj=enrollment)
    
    # Populate student and course choices
    students = Student.query.filter_by(active=True).all()
    form.student_id.choices = [(0, 'Chọn học sinh')] + [(s.id, s.full_name) for s in students]
    
    active_courses = Course.query.filter_by(active=True).all()
    form.course_id.choices = [(0, 'Chọn khóa học')] + [(c.id, c.name) for c in active_courses]
    
    if form.validate_on_submit():
        # Check if student is already enrolled in this course (if changing course)
        if enrollment.course_id != form.course_id.data:
            existing_enrollment = Enrollment.query.filter_by(
                student_id=form.student_id.data,
                course_id=form.course_id.data,
                active=True
            ).first()
            
            if existing_enrollment:
                flash('Học sinh đã đăng ký khóa học này.', 'danger')
                return render_template('enrollment_form.html', form=form, enrollment=enrollment)
            
            # Check if course has reached max students
            course = Course.query.get(form.course_id.data)
            current_enrollments = Enrollment.query.filter_by(
                course_id=form.course_id.data,
                active=True
            ).count()
            
            if current_enrollments >= course.max_students:
                flash('Khóa học đã đạt số lượng học sinh tối đa.', 'danger')
                return render_template('enrollment_form.html', form=form, enrollment=enrollment)
        
        enrollment.student_id = form.student_id.data
        enrollment.course_id = form.course_id.data
        enrollment.enrollment_date = form.enrollment_date.data
        enrollment.fee_paid = form.fee_paid.data
        enrollment.payment_status = form.payment_status.data
        enrollment.payment_date = form.payment_date.data
        
        db.session.commit()
        
        flash('Cập nhật đăng ký thành công.', 'success')
        return redirect(url_for('course_detail', course_id=enrollment.course_id))
    
    return render_template('enrollment_form.html', form=form, enrollment=enrollment)

@app.route('/enrollments/<int:enrollment_id>/delete', methods=['POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def delete_enrollment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    course_id = enrollment.course_id
    
    db.session.delete(enrollment)
    db.session.commit()
    
    flash('Đã hủy đăng ký khóa học.', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

# Attendance routes
@app.route('/attendance')
@login_required
def attendance_dashboard():
    # Get all active courses
    if current_user.role == 'teacher':
        active_courses = Course.query.filter_by(
            teacher_id=current_user.id,
            active=True
        ).all()
    else:
        active_courses = Course.query.filter_by(active=True).all()
    
    # Get today's attendance records
    today = date.today()
    today_student_attendance = StudentAttendance.query.filter_by(date=today).all()
    today_teacher_attendance = TeacherAttendance.query.filter_by(date=today).all()
    
    # Get recent attendance records
    recent_student_attendance = StudentAttendance.query.order_by(
        StudentAttendance.date.desc()
    ).limit(20).all()
    
    recent_teacher_attendance = TeacherAttendance.query.order_by(
        TeacherAttendance.date.desc()
    ).limit(20).all()
    
    return render_template(
        'attendance.html',
        active_courses=active_courses,
        today=today,
        today_student_attendance=today_student_attendance,
        today_teacher_attendance=today_teacher_attendance,
        recent_student_attendance=recent_student_attendance,
        recent_teacher_attendance=recent_teacher_attendance
    )

@app.route('/attendance/student/<int:course_id>', methods=['GET', 'POST'])
@login_required
def student_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if user has permission to take attendance
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('Bạn không có quyền điểm danh cho khóa học này.', 'danger')
        return redirect(url_for('attendance_dashboard'))
    
    # Get all students enrolled in this course
    students = Student.query.join(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.active == True,
        Student.active == True
    ).all()
    
    if not students:
        flash('Không có học sinh nào đăng ký khóa học này.', 'info')
        return redirect(url_for('attendance_dashboard'))
    
    # Get the attendance date (default to today)
    attendance_date = request.args.get('date')
    if attendance_date:
        attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
    else:
        attendance_date = date.today()
    
    # Get existing attendance records for this date and course
    existing_attendance = StudentAttendance.query.filter_by(
        course_id=course_id,
        date=attendance_date
    ).all()
    
    existing_attendance_dict = {att.student_id: att for att in existing_attendance}
    
    if request.method == 'POST':
        for student in students:
            status = request.form.get(f'status_{student.id}')
            remark = request.form.get(f'remark_{student.id}')
            
            if student.id in existing_attendance_dict:
                # Update existing record
                attendance = existing_attendance_dict[student.id]
                attendance.status = status
                attendance.remark = remark
            else:
                # Create new record
                attendance = StudentAttendance(
                    student_id=student.id,
                    course_id=course_id,
                    date=attendance_date,
                    status=status,
                    remark=remark
                )
                db.session.add(attendance)
        
        db.session.commit()
        
        flash('Điểm danh học sinh đã được cập nhật thành công.', 'success')
        return redirect(url_for('attendance_dashboard'))
    
    return render_template(
        'student_attendance_form.html',
        course=course,
        students=students,
        attendance_date=attendance_date,
        existing_attendance=existing_attendance_dict
    )

@app.route('/attendance/teacher/<int:course_id>', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def teacher_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    
    if not course.teacher_id:
        flash('Khóa học này chưa có giáo viên.', 'info')
        return redirect(url_for('attendance_dashboard'))
    
    teacher = User.query.get(course.teacher_id)
    
    # Get the attendance date (default to today)
    attendance_date = request.args.get('date')
    if attendance_date:
        attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
    else:
        attendance_date = date.today()
    
    # Get existing attendance record for this date, course, and teacher
    existing_attendance = TeacherAttendance.query.filter_by(
        course_id=course_id,
        teacher_id=teacher.id,
        date=attendance_date
    ).first()
    
    form = TeacherAttendanceForm(obj=existing_attendance)
    
    if form.validate_on_submit():
        if existing_attendance:
            # Update existing record
            existing_attendance.status = form.status.data
            existing_attendance.remark = form.remark.data
        else:
            # Create new record
            attendance = TeacherAttendance(
                teacher_id=teacher.id,
                course_id=course_id,
                date=attendance_date,
                status=form.status.data,
                remark=form.remark.data
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        flash('Điểm danh giáo viên đã được cập nhật thành công.', 'success')
        return redirect(url_for('attendance_dashboard'))
    
    return render_template(
        'teacher_attendance_form.html',
        form=form,
        course=course,
        teacher=teacher,
        attendance_date=attendance_date
    )

# Assessment routes
@app.route('/assessments')
@login_required
def assessments():
    search_form = SearchForm()
    query = Assessment.query
    
    if current_user.role == 'teacher':
        # Teachers can only see their own assessments
        query = query.filter_by(teacher_id=current_user.id)
    
    search_term = request.args.get('search', '')
    if search_term:
        # Join with Student to search by student name
        query = query.join(Student).filter(
            Student.full_name.ilike(f'%{search_term}%')
        )
    
    date_filter = request.args.get('date')
    if date_filter:
        query = query.filter(Assessment.date == datetime.strptime(date_filter, '%Y-%m-%d').date())
    
    assessments = query.order_by(Assessment.date.desc()).all()
    
    return render_template(
        'assessments.html',
        assessments=assessments,
        search_form=search_form,
        search_term=search_term,
        date_filter=date_filter
    )

@app.route('/assessments/add', methods=['GET', 'POST'])
@login_required
def add_assessment():
    form = AssessmentForm()
    
    # Populate student choices
    if current_user.role == 'teacher':
        # Teachers can only assess students in their courses
        students = Student.query.join(Enrollment).join(Course).filter(
            Course.teacher_id == current_user.id,
            Enrollment.active == True,
            Student.active == True
        ).distinct().all()
    else:
        students = Student.query.filter_by(active=True).all()
    
    form.student_id.choices = [(0, 'Chọn học sinh')] + [(s.id, s.full_name) for s in students]
    
    if form.validate_on_submit():
        assessment = Assessment(
            student_id=form.student_id.data,
            teacher_id=current_user.id,
            date=form.date.data or date.today(),
            content=form.content.data,
            email_sent=False
        )
        
        db.session.add(assessment)
        db.session.commit()
        
        # Send email if requested
        if form.send_email.data:
            student = Student.query.get(form.student_id.data)
            success = send_assessment_email(student, assessment, current_user)
            
            if success:
                assessment.email_sent = True
                db.session.commit()
                flash('Đánh giá đã được tạo và email đã được gửi thành công.', 'success')
            else:
                flash('Đánh giá đã được tạo nhưng không thể gửi email.', 'warning')
        else:
            flash('Đánh giá đã được tạo thành công.', 'success')
        
        return redirect(url_for('assessments'))
    
    return render_template('assessment_form.html', form=form)

@app.route('/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # Check if user has permission to edit this assessment
    if current_user.role == 'teacher' and assessment.teacher_id != current_user.id:
        flash('Bạn không có quyền chỉnh sửa đánh giá này.', 'danger')
        return redirect(url_for('assessments'))
    
    form = AssessmentForm(obj=assessment)
    
    # Populate student choices
    if current_user.role == 'teacher':
        # Teachers can only assess students in their courses
        students = Student.query.join(Enrollment).join(Course).filter(
            Course.teacher_id == current_user.id,
            Enrollment.active == True,
            Student.active == True
        ).distinct().all()
    else:
        students = Student.query.filter_by(active=True).all()
    
    form.student_id.choices = [(0, 'Chọn học sinh')] + [(s.id, s.full_name) for s in students]
    
    if form.validate_on_submit():
        assessment.student_id = form.student_id.data
        assessment.date = form.date.data
        assessment.content = form.content.data
        
        db.session.commit()
        
        # Send email if requested
        if form.send_email.data:
            student = Student.query.get(form.student_id.data)
            success = send_assessment_email(student, assessment, current_user)
            
            if success:
                assessment.email_sent = True
                db.session.commit()
                flash('Đánh giá đã được cập nhật và email đã được gửi thành công.', 'success')
            else:
                flash('Đánh giá đã được cập nhật nhưng không thể gửi email.', 'warning')
        else:
            flash('Đánh giá đã được cập nhật thành công.', 'success')
        
        return redirect(url_for('assessments'))
    
    return render_template('assessment_form.html', form=form, assessment=assessment)

@app.route('/assessments/<int:assessment_id>/delete', methods=['POST'])
@login_required
def delete_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # Check if user has permission to delete this assessment
    if current_user.role == 'teacher' and assessment.teacher_id != current_user.id:
        flash('Bạn không có quyền xóa đánh giá này.', 'danger')
        return redirect(url_for('assessments'))
    
    db.session.delete(assessment)
    db.session.commit()
    
    flash('Đánh giá đã được xóa thành công.', 'success')
    return redirect(url_for('assessments'))

@app.route('/assessments/<int:assessment_id>/send-email', methods=['POST'])
@login_required
def send_assessment_email_route(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    student = Student.query.get(assessment.student_id)
    teacher = User.query.get(assessment.teacher_id)
    
    success = send_assessment_email(student, assessment, teacher)
    
    if success:
        assessment.email_sent = True
        db.session.commit()
        flash('Email đã được gửi thành công.', 'success')
    else:
        flash('Không thể gửi email.', 'danger')
    
    return redirect(url_for('assessments'))

# Salary management routes
@app.route('/salaries')
@login_required
@requires_roles(['sadmin', 'admin'])
def salaries():
    search_form = SearchForm()
    query = TeacherSalary.query
    
    search_term = request.args.get('search', '')
    if search_term:
        # Join with User to search by teacher name
        query = query.join(User).filter(
            User.full_name.ilike(f'%{search_term}%')
        )
    
    month_filter = request.args.get('month')
    if month_filter:
        query = query.filter_by(month=int(month_filter))
    
    year_filter = request.args.get('year')
    if year_filter:
        query = query.filter_by(year=int(year_filter))
    
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    
    salaries = query.order_by(TeacherSalary.year.desc(), TeacherSalary.month.desc()).all()
    
    # Calculate total salary amount
    total_amount = db.session.query(func.sum(TeacherSalary.amount)).scalar() or 0
    
    # Calculate pending salary amount
    pending_amount = db.session.query(
        func.sum(TeacherSalary.amount)
    ).filter_by(
        payment_status='pending'
    ).scalar() or 0
    
    return render_template(
        'salaries.html',
        salaries=salaries,
        search_form=search_form,
        search_term=search_term,
        month_filter=month_filter,
        year_filter=year_filter,
        status_filter=status_filter,
        total_amount=total_amount,
        pending_amount=pending_amount
    )

@app.route('/salaries/add', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def add_salary():
    form = TeacherSalaryForm()
    
    # Populate teacher choices
    teachers = User.query.filter_by(role='teacher', active=True).all()
    form.teacher_id.choices = [(0, 'Chọn giáo viên')] + [(t.id, t.full_name) for t in teachers]
    
    if form.validate_on_submit():
        # Check if salary record already exists for this teacher, month and year
        existing_salary = TeacherSalary.query.filter_by(
            teacher_id=form.teacher_id.data,
            month=form.month.data,
            year=form.year.data
        ).first()
        
        if existing_salary:
            flash('Bản ghi lương đã tồn tại cho giáo viên này trong tháng và năm đã chọn.', 'danger')
            return render_template('salary_form.html', form=form)
        
        # Calculate the number of sessions taught
        start_date = date(form.year.data, form.month.data, 1)
        if form.month.data == 12:
            end_date = date(form.year.data + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(form.year.data, form.month.data + 1, 1) - timedelta(days=1)
        
        sessions_count = TeacherAttendance.query.filter(
            TeacherAttendance.teacher_id == form.teacher_id.data,
            TeacherAttendance.date.between(start_date, end_date),
            TeacherAttendance.status == 'present'
        ).count()
        
        salary = TeacherSalary(
            teacher_id=form.teacher_id.data,
            month=form.month.data,
            year=form.year.data,
            sessions_count=sessions_count,
            amount=form.amount.data,
            payment_date=form.payment_date.data,
            payment_status=form.payment_status.data,
            remark=form.remark.data
        )
        
        db.session.add(salary)
        db.session.commit()
        
        flash('Bản ghi lương đã được tạo thành công.', 'success')
        return redirect(url_for('salaries'))
    
    return render_template('salary_form.html', form=form)

@app.route('/salaries/<int:salary_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def edit_salary(salary_id):
    salary = TeacherSalary.query.get_or_404(salary_id)
    form = TeacherSalaryForm(obj=salary)
    
    # Populate teacher choices
    teachers = User.query.filter_by(role='teacher', active=True).all()
    form.teacher_id.choices = [(0, 'Chọn giáo viên')] + [(t.id, t.full_name) for t in teachers]
    
    if form.validate_on_submit():
        # Check if salary record already exists for this teacher, month and year (except this one)
        existing_salary = TeacherSalary.query.filter(
            TeacherSalary.teacher_id == form.teacher_id.data,
            TeacherSalary.month == form.month.data,
            TeacherSalary.year == form.year.data,
            TeacherSalary.id != salary_id
        ).first()
        
        if existing_salary:
            flash('Bản ghi lương đã tồn tại cho giáo viên này trong tháng và năm đã chọn.', 'danger')
            return render_template('salary_form.html', form=form, salary=salary)
        
        salary.teacher_id = form.teacher_id.data
        salary.month = form.month.data
        salary.year = form.year.data
        salary.amount = form.amount.data
        salary.payment_date = form.payment_date.data
        salary.payment_status = form.payment_status.data
        salary.remark = form.remark.data
        
        db.session.commit()
        
        flash('Bản ghi lương đã được cập nhật thành công.', 'success')
        return redirect(url_for('salaries'))
    
    return render_template('salary_form.html', form=form, salary=salary)

@app.route('/salaries/<int:salary_id>/delete', methods=['POST'])
@login_required
@requires_roles(['sadmin', 'admin'])
def delete_salary(salary_id):
    salary = TeacherSalary.query.get_or_404(salary_id)
    
    db.session.delete(salary)
    db.session.commit()
    
    flash('Bản ghi lương đã được xóa thành công.', 'success')
    return redirect(url_for('salaries'))

# Messages routes
@app.route('/messages')
@login_required
def messages():
    # Default to inbox
    folder = request.args.get('folder', 'inbox')
    
    if folder == 'inbox':
        messages = Message.query.filter_by(
            recipient_id=current_user.id
        ).order_by(Message.created_at.desc()).all()
    else:  # sent
        messages = Message.query.filter_by(
            sender_id=current_user.id
        ).order_by(Message.created_at.desc()).all()
    
    # Count unread messages
    unread_count = Message.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).count()
    
    return render_template(
        'messages.html',
        messages=messages,
        folder=folder,
        unread_count=unread_count
    )

@app.route('/messages/compose', methods=['GET', 'POST'])
@login_required
def compose_message():
    form = MessageForm()
    
    # Populate recipient choices (all active users except current user)
    recipients = User.query.filter(
        User.active == True,
        User.id != current_user.id
    ).all()
    
    form.recipient_id.choices = [(0, 'Chọn người nhận')] + [(r.id, r.full_name) for r in recipients]
    
    # Pre-fill recipient if provided in URL
    recipient_id = request.args.get('recipient_id')
    if recipient_id and not form.is_submitted():
        form.recipient_id.data = int(recipient_id)
    
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=form.recipient_id.data,
            subject=form.subject.data,
            content=form.content.data,
            read=False,
            created_at=datetime.now()
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Tin nhắn đã được gửi thành công.', 'success')
        return redirect(url_for('messages'))
    
    return render_template('message_form.html', form=form)

@app.route('/messages/<int:message_id>')
@login_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Check if user has permission to view this message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        flash('Bạn không có quyền xem tin nhắn này.', 'danger')
        return redirect(url_for('messages'))
    
    # Mark as read if current user is the recipient
    if message.recipient_id == current_user.id and not message.read:
        message.read = True
        db.session.commit()
    
    return render_template('message_detail.html', message=message)

@app.route('/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Check if user has permission to delete this message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        flash('Bạn không có quyền xóa tin nhắn này.', 'danger')
        return redirect(url_for('messages'))
    
    db.session.delete(message)
    db.session.commit()
    
    flash('Tin nhắn đã được xóa thành công.', 'success')
    return redirect(url_for('messages'))

@app.route('/messages/<int:message_id>/reply', methods=['GET', 'POST'])
@login_required
def reply_message(message_id):
    original_message = Message.query.get_or_404(message_id)
    
    # Check if user has permission to reply to this message
    if original_message.recipient_id != current_user.id:
        flash('Bạn không có quyền trả lời tin nhắn này.', 'danger')
        return redirect(url_for('messages'))
    
    form = MessageForm()
    
    # Populate recipient choices (all active users except current user)
    recipients = User.query.filter(
        User.active == True,
        User.id != current_user.id
    ).all()
    
    form.recipient_id.choices = [(0, 'Chọn người nhận')] + [(r.id, r.full_name) for r in recipients]
    
    # Pre-fill recipient and subject
    if not form.is_submitted():
        form.recipient_id.data = original_message.sender_id
        form.subject.data = f"Re: {original_message.subject}"
    
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=form.recipient_id.data,
            subject=form.subject.data,
            content=form.content.data,
            read=False,
            created_at=datetime.now()
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Tin nhắn trả lời đã được gửi thành công.', 'success')
        return redirect(url_for('messages'))
    
    return render_template(
        'message_form.html',
        form=form,
        is_reply=True,
        original_message=original_message
    )

# API routes for AJAX calls
@app.route('/api/course/<int:course_id>/info')
@login_required
def get_course_info(course_id):
    course = Course.query.get_or_404(course_id)
    
    return jsonify({
        'id': course.id,
        'name': course.name,
        'fee': course.fee,
        'studentCount': course.current_students_count,
        'maxStudents': course.max_students
    })
