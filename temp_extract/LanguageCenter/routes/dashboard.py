from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models import Student, Course, Payment, Enrollment, User
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    # Get counts for basic statistics
    stats = {}
    stats['total_students'] = Student.query.filter_by(active=True).count()
    stats['total_courses'] = Course.query.filter_by(active=True).count()
    
    # Total revenue
    total_revenue = db.session.query(func.sum(Payment.amount)).scalar() or 0
    stats['total_revenue'] = total_revenue
    
    # Get recent payments (last 5)
    recent_payments = Payment.query.order_by(Payment.payment_date.desc()).limit(5).all()
    
    # Get upcoming courses (courses starting in the next 30 days)
    today = datetime.now().date()
    thirty_days_later = today + timedelta(days=30)
    upcoming_courses = Course.query.filter(
        Course.start_date >= today,
        Course.start_date <= thirty_days_later,
        Course.active == True
    ).order_by(Course.start_date).all()
    
    # Get courses taught by the current teacher
    teacher_courses = []
    if current_user.role == 'teacher':
        teacher_courses = Course.query.filter_by(
            teacher_id=current_user.id,
            active=True
        ).order_by(Course.start_date).all()
    
    # Get new students (joined in the last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_students = Student.query.filter(
        Student.date_joined >= thirty_days_ago,
        Student.active == True
    ).order_by(Student.date_joined.desc()).all()
    
    # Monthly revenue data for chart (last 6 months)
    monthly_revenue = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=i*30)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        if month_end.month != month_start.month:
            month_end = month_end.replace(day=1) - timedelta(days=1)
        
        month_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.payment_date >= month_start,
            Payment.payment_date <= month_end
        ).scalar() or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(month_revenue)
        })
    
    # Course enrollment distribution for chart
    course_enrollments = []
    courses = Course.query.filter_by(active=True).all()
    for course in courses:
        enrollment_count = Enrollment.query.filter_by(course_id=course.id).count()
        if enrollment_count > 0:
            course_enrollments.append({
                'course': course.name,
                'students': enrollment_count
            })
    
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_payments=recent_payments,
        upcoming_courses=upcoming_courses,
        teacher_courses=teacher_courses,
        new_students=new_students,
        monthly_revenue=monthly_revenue,
        course_enrollments=course_enrollments
    )


@dashboard_bp.route('/reports')
@login_required
def reports():
    # Only admin can access full reports
    if current_user.role != 'admin':
        return redirect(url_for('dashboard.index'))
    
    # Get all active courses
    active_courses = Course.query.filter_by(active=True).all()
    
    # Course statistics
    course_stats = []
    for course in active_courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).count()
        payments = db.session.query(func.sum(Payment.amount)).filter_by(course_id=course.id).scalar() or 0
        
        course_stats.append({
            'course': course,
            'enrollments': enrollments,
            'payments': float(payments),
            'potential_revenue': course.price * course.max_students,
            'current_revenue': float(payments),
            'fill_rate': (enrollments / course.max_students * 100) if course.max_students > 0 else 0
        })
    
    # Teacher statistics
    teacher_stats = []
    teachers = User.query.filter_by(role='teacher').all()
    for teacher in teachers:
        courses_count = Course.query.filter_by(teacher_id=teacher.id).count()
        teacher_courses = Course.query.filter_by(teacher_id=teacher.id).all()
        course_ids = [c.id for c in teacher_courses]
        
        enrollments = Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).count() if course_ids else 0
        
        payments = 0
        if course_ids:
            payments = db.session.query(func.sum(Payment.amount)).filter(Payment.course_id.in_(course_ids)).scalar() or 0
        
        teacher_stats.append({
            'teacher': teacher,
            'courses_count': courses_count,
            'enrollments': enrollments,
            'revenue': float(payments)
        })
    
    return render_template(
        'reports.html',
        course_stats=course_stats,
        teacher_stats=teacher_stats
    )
