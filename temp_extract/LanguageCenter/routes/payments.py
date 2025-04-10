from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models import Payment, Student, Course
from utils.helpers import generate_receipt_number
from utils.email import send_receipt_email

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


@payments_bp.route('/')
@login_required
def index():
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    return render_template('payments/index.html', payments=payments)


@payments_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        
        # Validate inputs
        if not student_id or not course_id or not amount:
            flash('Tất cả các trường là bắt buộc.', 'danger')
            return redirect(url_for('payments.add'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError('Số tiền phải là số dương')
        except ValueError:
            flash('Số tiền thanh toán không hợp lệ.', 'danger')
            return redirect(url_for('payments.add'))
        
        # Generate unique receipt number
        receipt_number = generate_receipt_number()
        
        # Create new payment
        new_payment = Payment(
            student_id=student_id,
            course_id=course_id,
            amount=amount,
            payment_method=payment_method,
            receipt_number=receipt_number
        )
        
        db.session.add(new_payment)
        db.session.commit()
        
        # Send receipt email
        student = Student.query.get(student_id)
        course = Course.query.get(course_id)
        try:
            send_receipt_email(student.email, receipt_number, amount, course.name, student.full_name)
            flash('Thanh toán đã được ghi nhận và email biên lai đã được gửi.', 'success')
        except Exception as e:
            flash(f'Thanh toán đã được ghi nhận nhưng không gửi được email: {str(e)}', 'warning')
        
        return redirect(url_for('payments.view_receipt', id=new_payment.id))
    
    # Get all students and courses for dropdown
    students = Student.query.filter_by(active=True).order_by(Student.last_name).all()
    courses = Course.query.filter_by(active=True).order_by(Course.name).all()
    
    return render_template('payments/add.html', students=students, courses=courses)


@payments_bp.route('/student/<int:student_id>/add', methods=['GET', 'POST'])
@login_required
def add_for_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        
        # Validate inputs
        if not course_id or not amount:
            flash('Tất cả các trường là bắt buộc.', 'danger')
            return redirect(url_for('payments.add_for_student', student_id=student_id))
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError('Số tiền phải là số dương')
        except ValueError:
            flash('Số tiền thanh toán không hợp lệ.', 'danger')
            return redirect(url_for('payments.add_for_student', student_id=student_id))
        
        # Generate unique receipt number
        receipt_number = generate_receipt_number()
        
        # Create new payment
        new_payment = Payment(
            student_id=student_id,
            course_id=course_id,
            amount=amount,
            payment_method=payment_method,
            receipt_number=receipt_number
        )
        
        db.session.add(new_payment)
        db.session.commit()
        
        # Send receipt email
        course = Course.query.get(course_id)
        try:
            send_receipt_email(student.email, receipt_number, amount, course.name, student.full_name)
            flash('Thanh toán đã được ghi nhận và email biên lai đã được gửi.', 'success')
        except Exception as e:
            flash(f'Thanh toán đã được ghi nhận nhưng không gửi được email: {str(e)}', 'warning')
        
        return redirect(url_for('payments.view_receipt', id=new_payment.id))
    
    # Get courses for which the student is enrolled
    enrollments = student.enrollments
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = Course.query.filter(Course.id.in_(course_ids)).all()
    
    return render_template(
        'payments/add.html', 
        student=student, 
        courses=courses, 
        for_student=True
    )


@payments_bp.route('/receipt/<int:id>')
@login_required
def view_receipt(id):
    payment = Payment.query.get_or_404(id)
    student = Student.query.get(payment.student_id)
    course = Course.query.get(payment.course_id)
    
    return render_template('payments/receipt.html', payment=payment, student=student, course=course)


@payments_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    # Only admin can delete payments
    if current_user.role != 'admin':
        flash('Bạn không có quyền xóa thanh toán.', 'danger')
        return redirect(url_for('payments.index'))
    
    payment = Payment.query.get_or_404(id)
    student_id = payment.student_id
    
    try:
        db.session.delete(payment)
        db.session.commit()
        flash('Thanh toán đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa thanh toán: {str(e)}', 'danger')
    
    # Redirect to student view if coming from there
    if request.referrer and f'/students/view/{student_id}' in request.referrer:
        return redirect(url_for('students.view', id=student_id))
    
    return redirect(url_for('payments.index'))
