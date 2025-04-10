from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from models import Student, Enrollment, Course, Payment, Attendance
from utils.helpers import generate_receipt_number, add_log

students_bp = Blueprint('students', __name__, url_prefix='/students')


@students_bp.route('/')
@login_required
def index():
    students = Student.query.order_by(Student.last_name).all()
    courses = Course.query.filter_by(active=True).all()
    today = date.today()
    return render_template('students/index.html', students=students, courses=courses, today=today)


@students_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        date_of_birth = request.form.get('date_of_birth')
        boarding_status = request.form.get('boarding_status', 'không')
        meal_fee_per_day = request.form.get('meal_fee_per_day', 0)
        
        # Validate data
        if Student.query.filter_by(email=email).first():
            flash('Một sinh viên có email đó đã tồn tại.', 'danger')
            return redirect(url_for('students.add'))
        
        # Parse date of birth
        dob = None
        if date_of_birth:
            try:
                dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                flash('Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.', 'danger')
                return redirect(url_for('students.add'))
        
        # Convert meal fee to float
        try:
            meal_fee_per_day = float(meal_fee_per_day)
        except ValueError:
            meal_fee_per_day = 0.0
                
        # Create new student
        new_student = Student(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            date_of_birth=dob,
            boarding_status=boarding_status,
            meal_fee_per_day=meal_fee_per_day
        )
        
        db.session.add(new_student)
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Thêm học sinh', f'Thêm học sinh mới: {first_name} {last_name} (ID: {new_student.id})')
        
        flash(f'Học sinh: {first_name} {last_name} đã được thêm thành công.', 'success')
        return redirect(url_for('students.index'))
    
    return render_template('students/add.html')


@students_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        date_of_birth = request.form.get('date_of_birth')
        boarding_status = request.form.get('boarding_status', 'không')
        meal_fee_per_day = request.form.get('meal_fee_per_day', 0)
        active = 'active' in request.form
        
        # Validate email uniqueness
        student_with_email = Student.query.filter_by(email=email).first()
        if student_with_email and student_with_email.id != id:
            flash('Email đã tồn tại cho một học viên khác.', 'danger')
            return redirect(url_for('students.edit', id=id))
        
        # Parse date of birth
        dob = None
        if date_of_birth:
            try:
                dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                flash('Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.', 'danger')
                return redirect(url_for('students.edit', id=id))
                
        # Convert meal fee to float
        try:
            meal_fee_per_day = float(meal_fee_per_day)
        except ValueError:
            meal_fee_per_day = 0.0
        
        # Update student
        student.first_name = first_name
        student.last_name = last_name
        student.email = email
        student.phone = phone
        student.address = address
        student.date_of_birth = dob
        student.boarding_status = boarding_status
        student.meal_fee_per_day = meal_fee_per_day
        student.active = active
        
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Cập nhật học sinh', f'Cập nhật thông tin học sinh: {student.first_name} {student.last_name} (ID: {id})')
        
        flash('Thông tin học viên được cập nhật thành công.', 'success')
        return redirect(url_for('students.view', id=id))
    
    return render_template('students/edit.html', student=student)


@students_bp.route('/view/<int:id>')
@login_required
def view(id):
    student = Student.query.get_or_404(id)
    enrollments = Enrollment.query.filter_by(student_id=id).all()
    payments = Payment.query.filter_by(student_id=id).order_by(Payment.payment_date.desc()).all()
    
    # Get available courses for enrollment
    available_courses = Course.query.filter(
        Course.active == True,
        ~Course.id.in_([e.course_id for e in enrollments])
    ).all()
    
    return render_template(
        'students/view.html', 
        student=student, 
        enrollments=enrollments, 
        payments=payments,
        available_courses=available_courses
    )


@students_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    # Only admin can delete students
    if current_user.role != 'admin':
        flash('Bạn không có quyền xóa học sinh.', 'danger')
        return redirect(url_for('students.index'))
    
    student = Student.query.get_or_404(id)
    
    try:
        student_name = f"{student.first_name} {student.last_name}"
        student_id = student.id
        db.session.delete(student)
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Xóa học sinh', f'Đã xóa học sinh: {student_name} (ID: {student_id})')
        
        flash('Học sinh đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa học sinh: {str(e)}', 'danger')
    
    return redirect(url_for('students.index'))


@students_bp.route('/enroll/<int:id>', methods=['POST'])
@login_required
def enroll(id):
    student = Student.query.get_or_404(id)
    course_id = request.form.get('course_id')
    
    if not course_id:
        flash('Vui lòng chọn một khóa học.', 'danger')
        return redirect(url_for('students.view', id=id))
    
    course = Course.query.get_or_404(course_id)
    
    # Check if the course is full
    if course.is_full:
        flash(f'Khóa học {course.name} đã đủ học sinh.', 'danger')
        return redirect(url_for('students.view', id=id))
    
    # Check if student is already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=id, course_id=course_id
    ).first()
    
    if existing_enrollment:
        flash(f'Học sinh đã đăng ký vào {course.name}.', 'danger')
        return redirect(url_for('students.view', id=id))
    
    # Create new enrollment
    new_enrollment = Enrollment(
        student_id=id,
        course_id=course_id,
        status='active'
    )
    
    db.session.add(new_enrollment)
    
    # Create initial payment record if payment is provided
    payment_amount = request.form.get('payment_amount')
    if payment_amount and float(payment_amount) > 0:
        payment_method = request.form.get('payment_method', 'cash')
        receipt_number = generate_receipt_number()
        
        new_payment = Payment(
            student_id=id,
            course_id=course_id,
            amount=float(payment_amount),
            payment_method=payment_method,
            receipt_number=receipt_number
        )
        
        db.session.add(new_payment)
    
    db.session.commit()
    
    # Ghi log hoạt động
    payment_info = ""
    if payment_amount and float(payment_amount) > 0:
        payment_info = f", kèm thanh toán {float(payment_amount)} ₫"
    add_log('Đăng ký khóa học', f'Học sinh {student.full_name} (ID: {student.id}) đã đăng ký khóa học {course.name} (ID: {course.id}){payment_info}')
    
    flash(f'Học sinh đã đăng ký vào {course.name}.', 'success')
    return redirect(url_for('students.view', id=id))


@students_bp.route('/unenroll/<int:student_id>/<int:course_id>', methods=['POST'])
@login_required
def unenroll(student_id, course_id):
    enrollment = Enrollment.query.filter_by(
        student_id=student_id, course_id=course_id
    ).first_or_404()
    
    # Only admin can unenroll students
    if current_user.role != 'admin':
        flash('Bạn không có quyền hủy đăng ký học sinh.', 'danger')
        return redirect(url_for('students.view', id=student_id))
    
    course = Course.query.get_or_404(course_id)
    
    if request.form.get('confirm') == 'yes':
        student = Student.query.get_or_404(student_id)
        db.session.delete(enrollment)
        db.session.commit()
        
        # Ghi log hoạt động
        add_log('Hủy đăng ký khóa học', f'Học sinh {student.full_name} (ID: {student_id}) đã bị hủy đăng ký khóa học {course.name} (ID: {course_id})')
        
        flash(f'Học sinh đã bị hủy đăng ký {course.name}.', 'success')
    
    return redirect(url_for('students.view', id=student_id))


@students_bp.route('/take-attendance', methods=['POST'])
@login_required
def take_attendance():
    """Xử lý điểm danh nhanh từ trang danh sách học sinh"""
    course_id = request.form.get('course_id')
    attendance_date_str = request.form.get('attendance_date')
    
    if not course_id:
        flash('Vui lòng chọn khóa học.', 'danger')
        return redirect(url_for('students.index'))
    
    # Chuyển đổi ngày điểm danh
    try:
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        attendance_date = date.today()
    
    # Lấy thông tin khóa học
    course = Course.query.get_or_404(course_id)
    
    # Lấy danh sách học sinh được chọn để điểm danh
    student_ids = request.form.getlist('student_id')
    
    if not student_ids:
        flash('Vui lòng chọn ít nhất một học sinh để điểm danh.', 'danger')
        return redirect(url_for('students.index'))
    
    # Đếm số lượng điểm danh thành công
    count = 0
    
    for student_id in student_ids:
        student_id = int(student_id)
        
        # Kiểm tra xem học sinh có đăng ký khóa học không
        enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
        if not enrollment:
            continue
        
        # Lấy thông tin điểm danh
        status = request.form.get(f'status_{student_id}', 'present')
        had_meal = f'had_meal_{student_id}' in request.form
        note = request.form.get(f'note_{student_id}', '')
        
        # Kiểm tra xem đã có bản ghi điểm danh cho học sinh này trong ngày này chưa
        attendance = Attendance.query.filter_by(
            student_id=student_id,
            course_id=course_id,
            date=attendance_date
        ).first()
        
        if attendance:
            # Cập nhật bản ghi hiện có
            attendance.status = status
            attendance.had_meal = had_meal
            attendance.note = note
            attendance.recorded_by = current_user.id
        else:
            # Tạo bản ghi mới
            attendance = Attendance(
                student_id=student_id,
                course_id=course_id,
                date=attendance_date,
                status=status,
                had_meal=had_meal,
                note=note,
                recorded_by=current_user.id
            )
            db.session.add(attendance)
        
        count += 1
    
    db.session.commit()
    
    # Ghi log hoạt động
    add_log('Điểm danh', f'Đã điểm danh cho {count} học sinh trong khóa học {course.name} (ID: {course_id}) ngày {attendance_date}')
    
    flash(f'Đã cập nhật điểm danh cho {count} học sinh trong khóa học {course.name}.', 'success')
    return redirect(url_for('students.index'))


@students_bp.route('/get-students/<int:course_id>')
@login_required
def get_students(course_id):
    """API để lấy danh sách học sinh trong một khóa học"""
    # Lấy danh sách học sinh đã đăng ký khóa học
    enrollments = Enrollment.query.filter_by(course_id=course_id, status='active').all()
    
    if not enrollments:
        return jsonify({'success': False, 'message': 'Không có học sinh nào đăng ký khóa học này.'})
    
    student_data = []
    for enrollment in enrollments:
        student = enrollment.student
        student_data.append({
            'id': student.id,
            'full_name': student.full_name,
            'boarding_status': student.boarding_status
        })
    
    return jsonify({'success': True, 'students': student_data})
