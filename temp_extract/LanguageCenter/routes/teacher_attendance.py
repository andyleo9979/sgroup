import os
from datetime import datetime, date, time
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from models import User, TeacherAttendance
from utils.helpers import format_currency

teacher_attendance_bp = Blueprint('teacher_attendance', __name__)


@teacher_attendance_bp.route('/')
@login_required
def index():
    """Hiển thị danh sách chấm công giáo viên theo ngày"""
    
    # Chỉ admin mới có quyền xem trang này
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy tham số lọc từ URL
    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)
    teacher_id = request.args.get('teacher_id', type=int)
    
    # Lấy danh sách giáo viên để hiển thị trong dropdown
    teachers = User.query.filter_by(role='teacher').all()
    
    # Thiết lập ngày đầu và cuối tháng
    if month == 12:
        start_date = date(year, month, 1)
        end_date = date(year + 1, 1, 1)
    else:
        start_date = date(year, month, 1)
        end_date = date(year, month + 1, 1)
    
    # Truy vấn dữ liệu
    query = TeacherAttendance.query.filter(
        TeacherAttendance.date >= start_date,
        TeacherAttendance.date < end_date
    )
    
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)
    
    attendances = query.order_by(TeacherAttendance.date.desc()).all()
    
    # Thống kê
    summary = {}
    for attendance in attendances:
        teacher_id = attendance.teacher_id
        if teacher_id not in summary:
            summary[teacher_id] = {
                'teacher': attendance.teacher,
                'total_days': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'leave': 0,
                'total_hours': 0
            }
        
        summary[teacher_id]['total_days'] += 1
        summary[teacher_id][attendance.status] += 1
        summary[teacher_id]['total_hours'] += attendance.working_hours
    
    return render_template(
        'teacher_attendance/index.html',
        attendances=attendances,
        teachers=teachers,
        summary=summary,
        year=year,
        month=month,
        selected_teacher=teacher_id,
        format_currency=format_currency
    )


@teacher_attendance_bp.route('/take', methods=['GET', 'POST'])
@login_required
def take_attendance():
    """Trang chấm công cho giáo viên"""
    
    # Chỉ admin mới có quyền truy cập trang này
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy danh sách giáo viên
    teachers = User.query.filter_by(role='teacher').all()
    
    # Xử lý form
    if request.method == 'POST':
        attendance_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        for teacher_id in request.form.getlist('teacher_id'):
            teacher_id = int(teacher_id)
            status_key = f'status_{teacher_id}'
            time_in_key = f'time_in_{teacher_id}'
            time_out_key = f'time_out_{teacher_id}'
            note_key = f'note_{teacher_id}'
            
            status = request.form.get(status_key, 'absent')
            time_in_str = request.form.get(time_in_key, '')
            time_out_str = request.form.get(time_out_key, '')
            note = request.form.get(note_key, '')
            
            # Xử lý time_in và time_out
            time_in = None
            if time_in_str:
                hour, minute = map(int, time_in_str.split(':'))
                time_in = time(hour, minute)
                
            time_out = None
            if time_out_str:
                hour, minute = map(int, time_out_str.split(':'))
                time_out = time(hour, minute)
            
            # Kiểm tra xem đã có bản ghi chấm công cho giáo viên vào ngày này chưa
            attendance = TeacherAttendance.query.filter_by(
                teacher_id=teacher_id, 
                date=attendance_date
            ).first()
            
            if attendance:
                # Cập nhật bản ghi hiện có
                attendance.status = status
                attendance.time_in = time_in
                attendance.time_out = time_out
                attendance.note = note
                attendance.recorded_by = current_user.id
            else:
                # Tạo bản ghi mới
                attendance = TeacherAttendance(
                    teacher_id=teacher_id,
                    date=attendance_date,
                    status=status,
                    time_in=time_in,
                    time_out=time_out,
                    note=note,
                    recorded_by=current_user.id
                )
                db.session.add(attendance)
        
        db.session.commit()
        flash('Đã cập nhật chấm công cho giáo viên thành công!', 'success')
        return redirect(url_for('teacher_attendance.index'))
    
    # Nếu là GET, lấy ngày từ tham số hoặc sử dụng ngày hiện tại
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Chuyển đổi selected_date từ chuỗi sang đối tượng date
    try:
        attendance_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        attendance_date = datetime.now().date()
    
    # Lấy dữ liệu chấm công hiện có cho ngày đã chọn
    existing_attendances = {}
    attendances = TeacherAttendance.query.filter_by(date=attendance_date).all()
    
    for attendance in attendances:
        existing_attendances[attendance.teacher_id] = attendance
    
    return render_template(
        'teacher_attendance/take.html',
        teachers=teachers,
        selected_date=selected_date,
        existing_attendances=existing_attendances
    )


@teacher_attendance_bp.route('/report')
@login_required
def report():
    """Báo cáo chấm công và tính lương giáo viên"""
    
    # Chỉ admin mới có quyền xem trang này
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy tham số lọc
    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)
    
    # Thiết lập ngày đầu và cuối tháng
    if month == 12:
        start_date = date(year, month, 1)
        end_date = date(year + 1, 1, 1)
    else:
        start_date = date(year, month, 1)
        end_date = date(year, month + 1, 1)
    
    # Lấy tất cả giáo viên
    teachers = User.query.filter_by(role='teacher').all()
    
    # Thống kê
    summary = {}
    for teacher in teachers:
        summary[teacher.id] = {
            'teacher': teacher,
            'total_days': 0,
            'present': 0,
            'absent': 0,
            'late': 0,
            'leave': 0,
            'total_hours': 0
        }
        
        # Đếm số ngày theo trạng thái
        attendances = TeacherAttendance.query.filter(
            TeacherAttendance.teacher_id == teacher.id,
            TeacherAttendance.date >= start_date,
            TeacherAttendance.date < end_date
        ).all()
        
        for attendance in attendances:
            summary[teacher.id]['total_days'] += 1
            summary[teacher.id][attendance.status] += 1
            summary[teacher.id]['total_hours'] += attendance.working_hours
    
    # Lấy dữ liệu biểu đồ
    chart_data = {
        'teacher_names': [t.full_name for t in teachers],
        'present_days': [summary[t.id]['present'] for t in teachers],
        'absent_days': [summary[t.id]['absent'] for t in teachers],
        'total_hours': [summary[t.id]['total_hours'] for t in teachers]
    }
    
    return render_template(
        'teacher_attendance/report.html',
        summary=summary,
        year=year,
        month=month,
        teachers=teachers,
        chart_data=chart_data,
        format_currency=format_currency
    )


@teacher_attendance_bp.route('/teacher/<int:teacher_id>')
@login_required
def teacher_detail(teacher_id):
    """Hiển thị chi tiết chấm công của một giáo viên"""
    
    # Kiểm tra quyền truy cập (admin hoặc chính giáo viên đó)
    if current_user.role != 'admin' and current_user.id != teacher_id:
        flash('Bạn không có quyền truy cập trang này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Lấy thông tin giáo viên
    teacher = User.query.get_or_404(teacher_id)
    
    # Lấy tham số lọc
    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)
    
    # Thiết lập ngày đầu và cuối tháng
    if month == 12:
        start_date = date(year, month, 1)
        end_date = date(year + 1, 1, 1)
    else:
        start_date = date(year, month, 1)
        end_date = date(year, month + 1, 1)
    
    # Lấy dữ liệu chấm công
    attendances = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher_id,
        TeacherAttendance.date >= start_date,
        TeacherAttendance.date < end_date
    ).order_by(TeacherAttendance.date).all()
    
    # Thống kê
    summary = {
        'total_days': len(attendances),
        'present': len([a for a in attendances if a.status == 'present']),
        'absent': len([a for a in attendances if a.status == 'absent']),
        'late': len([a for a in attendances if a.status == 'late']),
        'leave': len([a for a in attendances if a.status == 'leave']),
        'total_hours': sum(a.working_hours for a in attendances)
    }
    
    # Dữ liệu biểu đồ
    dates = [a.date.strftime('%d/%m') for a in attendances]
    hours = [a.working_hours for a in attendances]
    
    chart_data = {
        'dates': dates,
        'hours': hours
    }
    
    return render_template(
        'teacher_attendance/teacher.html',
        teacher=teacher,
        attendances=attendances,
        summary=summary,
        year=year,
        month=month,
        chart_data=chart_data
    )