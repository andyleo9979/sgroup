from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app import db
from models import Attendance, Course, Student, User, Enrollment
from datetime import datetime, date, timedelta
import calendar

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/')
@login_required
def index():
    """Hiển thị danh sách tất cả buổi điểm danh theo ngày"""
    courses = Course.query.filter_by(active=True).all()
    
    # Xử lý ngày bắt đầu và kết thúc
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    selected_date = date.today()

    try:
        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        else:
            from_date = selected_date

        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        else:
            to_date = selected_date
    except ValueError:
        from_date = to_date = selected_date

    # Query cơ bản
    attendance_query = Attendance.query.filter(
        Attendance.date >= from_date,
        Attendance.date <= to_date
    )

    # Nếu có course_id được chọn thì lọc theo khóa học
    course_id = request.args.get('course_id', type=int)
    if course_id:
        attendance_query = attendance_query.filter_by(course_id=course_id)
        selected_course = Course.query.get_or_404(course_id)
    else:
        selected_course = None

    # Nếu có student_id được chọn thì lọc theo học viên
    student_id = request.args.get('student_id', type=int)
    if student_id:
        attendance_query = attendance_query.filter_by(student_id=student_id)
        selected_student = Student.query.get_or_404(student_id)
    else:
        selected_student = None

    # Lấy danh sách học viên cho dropdown
    students = Student.query.filter_by(active=True).all()

    # Lấy kết quả và sắp xếp theo ngày
    attendances = attendance_query.order_by(Attendance.date.desc()).all()
    
    return render_template(
        'attendance/index.html',
        attendances=attendances,
        courses=courses,
        students=students,
        selected_date=selected_date,
        selected_course=selected_course,
        selected_student=selected_student,
        from_date=from_date,
        to_date=to_date
    )


@attendance_bp.route('/course/<int:course_id>')
@login_required
def course_attendance(course_id):
    """Hiển thị trang điểm danh cho một khóa học cụ thể"""
    course = Course.query.get_or_404(course_id)
    
    # Chỉ giáo viên phụ trách hoặc admin mới có thể xem/sửa điểm danh
    if not current_user.role == 'admin' and current_user.id != course.teacher_id:
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy danh sách học sinh đã đăng ký khóa học
    enrollments = Enrollment.query.filter_by(course_id=course_id, status='active').all()
    students = [enrollment.student for enrollment in enrollments]
    
    # Mặc định hiển thị ngày hôm nay
    selected_date = request.args.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    # Kiểm tra xem đã có bản ghi điểm danh cho ngày này chưa
    attendances = {}
    for student in students:
        attendance = Attendance.query.filter_by(
            student_id=student.id, 
            course_id=course_id,
            date=selected_date
        ).first()
        
        if attendance:
            attendances[student.id] = attendance
    
    # Lấy danh sách các ngày đã điểm danh cho khóa học này
    attendance_dates = db.session.query(Attendance.date).filter_by(course_id=course_id).distinct().all()
    attendance_dates = [date[0] for date in attendance_dates]
    
    return render_template(
        'attendance/course.html',
        course=course,
        students=students,
        selected_date=selected_date,
        attendances=attendances,
        attendance_dates=attendance_dates
    )


@attendance_bp.route('/take/<int:course_id>', methods=['POST'])
@login_required
def take_attendance(course_id):
    """Xử lý form điểm danh cho một khóa học"""
    from utils.email import send_attendance_email, send_comment_email
    course = Course.query.get_or_404(course_id)
    
    # Chỉ giáo viên phụ trách hoặc admin mới có thể thực hiện điểm danh
    if not current_user.role == 'admin' and current_user.id != course.teacher_id:
        flash('Bạn không có quyền thực hiện điểm danh.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy ngày điểm danh từ form
    attendance_date = request.form.get('attendance_date')
    if attendance_date:
        try:
            attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            attendance_date = date.today()
    else:
        attendance_date = date.today()
    
    # Xử lý dữ liệu điểm danh cho từng học sinh
    student_ids = request.form.getlist('student_id')
    
    for student_id in student_ids:
        student_id = int(student_id)
        
        # Kiểm tra xem học sinh này có đăng ký khóa học không
        enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
        if not enrollment:
            continue
        
        # Lấy trạng thái điểm danh
        status_key = f'status_{student_id}'
        status = request.form.get(status_key, 'absent')
        
        # Lấy thông tin ăn
        had_meal_key = f'had_meal_{student_id}'
        had_meal = request.form.get(had_meal_key) == 'on'
        
        # Lấy ghi chú nếu có
        note_key = f'note_{student_id}'
        comment_key = f'comment_{student_id}'
        note = request.form.get(note_key, '')
        comment = request.form.get(comment_key, '')
        
        # Kiểm tra xem đã có bản ghi điểm danh cho học sinh này trong ngày này chưa
        attendance = Attendance.query.filter_by(
            student_id=student_id,
            course_id=course_id,
            date=attendance_date
        ).first()
        
        if attendance:
            # Cập nhật bản ghi điểm danh hiện có
            attendance.status = status
            attendance.had_meal = had_meal
            attendance.note = note
            attendance.comment = comment
            attendance.recorded_by = current_user.id
        else:
            # Tạo bản ghi điểm danh mới
            attendance = Attendance(
                student_id=student_id,
                course_id=course_id,
                date=attendance_date,
                status=status,
                had_meal=had_meal,
                note=note,
                comment=comment,
                recorded_by=current_user.id
            )
            db.session.add(attendance)
            
            # Gửi email thông báo điểm danh
            try:
                send_attendance_email(
                    student_email=enrollment.student.email,
                    student_name=enrollment.student.full_name,
                    course_name=course.name,
                    date=attendance_date,
                    status=status,
                    had_meal=had_meal
                )
                
                # Nếu có comment thì gửi email thông báo nhận xét
                if comment:
                    send_comment_email(
                        student_email=enrollment.student.email,
                        student_name=enrollment.student.full_name,
                        course_name=course.name,
                        date=attendance_date,
                        comment=comment,
                        teacher_name=current_user.full_name
                    )
            except Exception as e:
                flash(f'Không thể gửi email thông báo: {str(e)}', 'warning')
    
    db.session.commit()
    flash('Điểm danh đã được lưu thành công!', 'success')
    
    return redirect(url_for('attendance.course_attendance', course_id=course_id, date=attendance_date.strftime('%Y-%m-%d')))


@attendance_bp.route('/report')
@login_required
def report():
    """Hiển thị báo cáo điểm danh và tiền ăn"""
    courses = Course.query.filter_by(active=True).all()
    
    # Lọc theo khóa học nếu có
    course_id = request.args.get('course_id', type=int)
    
    # Lọc theo tháng và năm
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        today = date.today()
        month = today.month
        year = today.year
    
    # Tạo các giá trị cho dropdown tháng và năm
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = range(date.today().year - 2, date.today().year + 1)
    
    # Lọc danh sách học sinh
    if course_id:
        enrollments = Enrollment.query.filter_by(course_id=course_id, status='active').all()
        students = [enrollment.student for enrollment in enrollments]
        selected_course = Course.query.get_or_404(course_id)
    else:
        students = Student.query.filter_by(active=True).all()
        selected_course = None
    
    # Tính số buổi tham gia và tiền ăn cho mỗi học sinh
    student_data = []
    
    for student in students:
        # Tính tổng số buổi tham gia trong tháng
        if course_id:
            attendance_count = student.total_attendances(course_id)
        else:
            attendance_count = student.total_attendances()
        
        # Tính tiền ăn trong tháng
        meal_fee = student.total_meal_fee(month, year)
        
        student_data.append({
            'student': student,
            'attendance_count': attendance_count,
            'meal_fee': meal_fee
        })
    
    return render_template(
        'attendance/report.html',
        courses=courses,
        selected_course=selected_course,
        student_data=student_data,
        months=months,
        years=years,
        selected_month=month,
        selected_year=year
    )


@attendance_bp.route('/student/<int:student_id>')
@login_required
def student_attendance(student_id):
    """Hiển thị chi tiết điểm danh của một học sinh"""
    student = Student.query.get_or_404(student_id)
    
    # Lọc theo khóa học nếu có
    course_id = request.args.get('course_id', type=int)
    
    # Lọc theo tháng và năm
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        today = date.today()
        month = today.month
        year = today.year
    
    # Tạo các giá trị cho dropdown tháng và năm
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = range(date.today().year - 2, date.today().year + 1)
    
    # Tính ngày đầu và cuối tháng
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Lấy tất cả bản ghi điểm danh của học sinh trong tháng đã chọn
    query = Attendance.query.filter(
        Attendance.student_id == student_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    if course_id:
        query = query.filter_by(course_id=course_id)
        course = Course.query.get_or_404(course_id)
    else:
        course = None
    
    attendances = query.order_by(Attendance.date.desc()).all()
    
    # Lấy danh sách khóa học của học sinh
    enrollments = Enrollment.query.filter_by(student_id=student_id, status='active').all()
    courses = [enrollment.course for enrollment in enrollments]
    
    # Tính tổng tiền ăn trong tháng
    meal_fee = student.total_meal_fee(month, year)
    
    return render_template(
        'attendance/student.html',
        student=student,
        attendances=attendances,
        courses=courses,
        selected_course=course,
        months=months,
        years=years,
        selected_month=month,
        selected_year=year,
        meal_fee=meal_fee
    )


@attendance_bp.route('/api/get-students/<int:course_id>')
@login_required
def api_get_students(course_id):
    """API để lấy danh sách học sinh trong một khóa học"""
    enrollments = Enrollment.query.filter_by(course_id=course_id, status='active').all()
    students = []
    
    for enrollment in enrollments:
        students.append({
            'id': enrollment.student_id,
            'name': enrollment.student.full_name,
            'boarding_status': enrollment.student.boarding_status
        })
    
    return jsonify(students)