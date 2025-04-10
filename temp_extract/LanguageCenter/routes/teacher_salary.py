from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from flask_login import login_required, current_user
from sqlalchemy import func, extract, and_, or_, desc

from app import db
from models import User, Course, TeacherClassSession, TeacherAttendance, TeacherSalary

teacher_salary_bp = Blueprint('teacher_salary', __name__)

@teacher_salary_bp.before_request
@login_required
def before_request():
    pass

@teacher_salary_bp.route('/')
def index():
    """Hiển thị danh sách lương giáo viên theo tháng"""
    # Lấy tháng và năm từ query params, mặc định là tháng hiện tại
    current_month = int(request.args.get('month', datetime.now().month))
    current_year = int(request.args.get('year', datetime.now().year))
    
    # Tạo danh sách tháng và năm để hiển thị trong dropdown
    months = list(range(1, 13))
    years = list(range(datetime.now().year - 5, datetime.now().year + 2))
    
    # Lấy danh sách các bản ghi lương tháng đã có
    salary_records = TeacherSalary.query.filter(
        TeacherSalary.month == current_month,
        TeacherSalary.year == current_year
    ).all()
    
    # Lấy danh sách giáo viên
    teachers = User.query.filter(User.role == 'teacher').all()
    
    # Tạo bản ghi lương cho giáo viên nếu chưa có
    for teacher in teachers:
        # Kiểm tra nếu đã có bản ghi lương cho giáo viên này trong tháng
        existing_record = next((s for s in salary_records if s.teacher_id == teacher.id), None)
        
        if not existing_record:
            # Tính lương dựa trên số buổi dạy và chấm công
            salary = TeacherSalary(
                teacher_id=teacher.id,
                month=current_month,
                year=current_year,
                status='pending'
            )
            
            # Lấy tất cả các buổi dạy của giáo viên trong tháng, nhóm theo khóa học
            teaching_sessions = TeacherClassSession.query.filter(
                TeacherClassSession.teacher_id == teacher.id,
                extract('month', TeacherClassSession.date) == current_month,
                extract('year', TeacherClassSession.date) == current_year
            ).all()
            
            # Tính lương cơ bản dựa trên đơn giá của từng khóa học
            base_salary = 0
            total_periods = 0
            
            for session in teaching_sessions:
                # Cộng tiền cho từng buổi dạy dựa trên đơn giá của khóa học
                course_rate = session.course.teaching_rate or 0
                session_pay = session.periods * course_rate
                base_salary += session_pay
                total_periods += session.periods
            
            # Tính khấu trừ từ bảng chấm công
            deductions = 0
            attendances = TeacherAttendance.query.filter(
                TeacherAttendance.teacher_id == teacher.id,
                extract('month', TeacherAttendance.date) == current_month,
                extract('year', TeacherAttendance.date) == current_year
            ).all()
            
            for attendance in attendances:
                if attendance.status == 'late':
                    deductions += (teacher.late_fee or 0)
                elif attendance.status == 'absent':
                    deductions += (teacher.absence_fee or 0)
            
            # Cập nhật thông tin lương
            salary.total_periods = total_periods
            salary.base_salary = base_salary
            salary.deductions = deductions
            salary.final_salary = max(0, base_salary - deductions)  # Đảm bảo lương không âm
            
            db.session.add(salary)
            
    # Commit các thay đổi
    db.session.commit()
    
    # Lấy lại danh sách lương sau khi đã tạo bản ghi mới
    updated_records = TeacherSalary.query.filter(
        TeacherSalary.month == current_month,
        TeacherSalary.year == current_year
    ).all()
    
    # Tạo danh sách kết hợp thông tin giáo viên và lương
    salary_data = []
    for record in updated_records:
        salary_data.append({
            'teacher': record.teacher,
            'salary': record
        })
    
    return render_template('teacher_salary/index.html', 
                           salary_data=salary_data,
                           months=months,
                           years=years,
                           current_month=current_month,
                           current_year=current_year)

@teacher_salary_bp.route('/sessions')
def sessions():
    """Hiển thị danh sách buổi dạy của giáo viên"""
    # Lấy tháng và năm từ query params, mặc định là tháng hiện tại
    current_month = int(request.args.get('month', datetime.now().month))
    current_year = int(request.args.get('year', datetime.now().year))
    teacher_id = request.args.get('teacher_id')
    
    # Tạo danh sách tháng và năm để hiển thị trong dropdown
    months = list(range(1, 13))
    years = list(range(datetime.now().year - 5, datetime.now().year + 2))
    
    # Tạo query cơ bản
    query = TeacherClassSession.query.filter(
        extract('month', TeacherClassSession.date) == current_month,
        extract('year', TeacherClassSession.date) == current_year
    )
    
    # Nếu có teacher_id, lọc theo giáo viên cụ thể
    teacher = None
    if teacher_id:
        query = query.filter(TeacherClassSession.teacher_id == teacher_id)
        teacher = User.query.get(teacher_id)
    elif current_user.role != 'admin':
        # Nếu không phải admin, chỉ hiển thị buổi dạy của giáo viên đang đăng nhập
        query = query.filter(TeacherClassSession.teacher_id == current_user.id)
        teacher = current_user
    
    # Lấy danh sách các buổi dạy, sắp xếp theo ngày giảm dần
    sessions = query.order_by(desc(TeacherClassSession.date)).all()
    
    return render_template('teacher_salary/sessions.html',
                           sessions=sessions,
                           months=months,
                           years=years,
                           current_month=current_month,
                           current_year=current_year,
                           teacher=teacher)

@teacher_salary_bp.route('/add-session', methods=['GET', 'POST'])
def add_session():
    """Thêm buổi dạy mới cho giáo viên"""
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        course_id = request.form.get('course_id')
        date_str = request.form.get('date')
        periods = int(request.form.get('periods', 1))
        note = request.form.get('note', '')
        
        # Kiểm tra quyền: chỉ admin mới có thể thêm cho người khác
        if current_user.role != 'admin' and int(teacher_id) != current_user.id:
            flash('Bạn không có quyền thêm buổi dạy cho giáo viên khác', 'danger')
            return redirect(url_for('teacher_salary.sessions'))
        
        try:
            # Kiểm tra nếu đã có bản ghi cho giáo viên, khóa học và ngày này
            existing = TeacherClassSession.query.filter_by(
                teacher_id=teacher_id,
                course_id=course_id,
                date=datetime.strptime(date_str, '%Y-%m-%d').date()
            ).first()
            
            if existing:
                flash('Đã tồn tại bản ghi buổi dạy cho giáo viên, khóa học và ngày này', 'warning')
                return redirect(url_for('teacher_salary.add_session'))
            
            # Tạo bản ghi mới
            session = TeacherClassSession(
                teacher_id=teacher_id,
                course_id=course_id,
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                periods=periods,
                note=note
            )
            
            db.session.add(session)
            db.session.commit()
            
            flash('Đã thêm buổi dạy thành công', 'success')
            return redirect(url_for('teacher_salary.sessions'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm buổi dạy: {str(e)}', 'danger')
    
    # GET request - hiển thị form
    teachers = User.query.filter(User.role == 'teacher').all()
    courses = Course.query.filter(Course.active == True).all()
    
    # Mặc định chọn ngày hôm nay
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('teacher_salary/add_session.html',
                           teachers=teachers,
                           courses=courses,
                           today=today)

@teacher_salary_bp.route('/edit-session/<int:id>', methods=['GET', 'POST'])
def edit_session(id):
    """Chỉnh sửa thông tin buổi dạy"""
    # Lấy thông tin buổi dạy
    session = TeacherClassSession.query.get_or_404(id)
    
    # Kiểm tra quyền: chỉ admin hoặc giáo viên của buổi dạy mới có thể chỉnh sửa
    if current_user.role != 'admin' and session.teacher_id != current_user.id:
        flash('Bạn không có quyền chỉnh sửa buổi dạy này', 'danger')
        return redirect(url_for('teacher_salary.sessions'))
    
    if request.method == 'POST':
        try:
            # Cập nhật thông tin buổi dạy
            if current_user.role == 'admin':
                session.teacher_id = request.form.get('teacher_id')
                session.course_id = request.form.get('course_id')
            
            date_str = request.form.get('date')
            session.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            session.periods = int(request.form.get('periods', 1))
            session.note = request.form.get('note', '')
            
            db.session.commit()
            
            flash('Đã cập nhật buổi dạy thành công', 'success')
            return redirect(url_for('teacher_salary.sessions'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật buổi dạy: {str(e)}', 'danger')
    
    # GET request - hiển thị form
    teachers = User.query.filter(User.role == 'teacher').all()
    courses = Course.query.filter(Course.active == True).all()
    
    return render_template('teacher_salary/edit_session.html',
                           session=session,
                           teachers=teachers,
                           courses=courses)

@teacher_salary_bp.route('/delete-session/<int:id>', methods=['POST'])
def delete_session(id):
    """Xóa buổi dạy"""
    session = TeacherClassSession.query.get_or_404(id)
    
    # Kiểm tra quyền: chỉ admin hoặc giáo viên của buổi dạy mới có thể xóa
    if current_user.role != 'admin' and session.teacher_id != current_user.id:
        flash('Bạn không có quyền xóa buổi dạy này', 'danger')
        return redirect(url_for('teacher_salary.sessions'))
    
    try:
        db.session.delete(session)
        db.session.commit()
        flash('Đã xóa buổi dạy thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa buổi dạy: {str(e)}', 'danger')
    
    return redirect(url_for('teacher_salary.sessions'))

@teacher_salary_bp.route('/update-salary-status/<int:id>', methods=['POST'])
def update_salary_status(id):
    """Cập nhật trạng thái lương giáo viên"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này', 'danger')
        return redirect(url_for('teacher_salary.index'))
    
    salary = TeacherSalary.query.get_or_404(id)
    status = request.form.get('status')
    
    if status not in ['pending', 'approved', 'paid']:
        flash('Trạng thái không hợp lệ', 'danger')
        return redirect(url_for('teacher_salary.index'))
    
    try:
        salary.status = status
        if status == 'paid':
            salary.payment_date = datetime.now()
        
        db.session.commit()
        flash('Đã cập nhật trạng thái lương thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi cập nhật trạng thái lương: {str(e)}', 'danger')
    
    return redirect(url_for('teacher_salary.index', month=salary.month, year=salary.year))

@teacher_salary_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Cài đặt đơn giá tiết dạy theo khóa học"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('teacher_salary.index'))
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        teaching_rate = request.form.get('teaching_rate')
        
        if not course_id:
            flash('Vui lòng chọn khóa học', 'warning')
            return redirect(url_for('teacher_salary.settings'))
        
        try:
            course = Course.query.get(course_id)
            
            if teaching_rate:
                course.teaching_rate = float(teaching_rate)
            
            db.session.commit()
            flash('Đã cập nhật đơn giá tiết dạy cho khóa học thành công', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật đơn giá tiết dạy: {str(e)}', 'danger')
    
    # Lấy danh sách giáo viên và khóa học
    teachers = User.query.filter(User.role == 'teacher').all()
    courses = Course.query.filter(Course.active == True).all()
    
    return render_template('teacher_salary/settings.html', teachers=teachers, courses=courses)

@teacher_salary_bp.route('/update-fee-settings', methods=['POST'])
def update_fee_settings():
    """Cập nhật các khoản phí trừ cho giáo viên"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này', 'danger')
        return redirect(url_for('teacher_salary.settings'))
    
    teacher_id = request.form.get('teacher_id')
    late_fee = request.form.get('late_fee')
    absence_fee = request.form.get('absence_fee')
    
    if not teacher_id:
        flash('Vui lòng chọn giáo viên', 'warning')
        return redirect(url_for('teacher_salary.settings'))
    
    try:
        teacher = User.query.get(teacher_id)
        
        if late_fee:
            teacher.late_fee = float(late_fee)
        if absence_fee:
            teacher.absence_fee = float(absence_fee)
        
        db.session.commit()
        flash('Đã cập nhật phí trừ cho giáo viên thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi cập nhật phí trừ: {str(e)}', 'danger')
    
    return redirect(url_for('teacher_salary.settings'))

@teacher_salary_bp.route('/api/course-rate/<int:course_id>')
def get_course_rate(course_id):
    """API để lấy thông tin đơn giá tiết dạy của khóa học"""
    course = Course.query.get_or_404(course_id)
    
    rate = {
        'teaching_rate': course.teaching_rate
    }
    
    return jsonify(rate)

@teacher_salary_bp.route('/api/teacher-fees/<int:teacher_id>')
def get_teacher_fees(teacher_id):
    """API để lấy thông tin phí trừ của giáo viên"""
    teacher = User.query.get_or_404(teacher_id)
    
    fees = {
        'late_fee': teacher.late_fee,
        'absence_fee': teacher.absence_fee
    }
    
    return jsonify(fees)