from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, current_app
from flask_login import login_required, current_user
import os
import tempfile
from werkzeug.utils import secure_filename

from utils.excel import create_student_template, create_teacher_template, process_student_import, process_teacher_import

import_bp = Blueprint('import_data', __name__)

@import_bp.route('/')
@login_required
def index():
    """Hiển thị trang chọn loại dữ liệu để nhập"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập tính năng này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    return render_template('import_data/index.html')

@import_bp.route('/students', methods=['GET', 'POST'])
@login_required
def import_students():
    """Nhập danh sách học sinh từ file Excel"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập tính năng này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'excel_file' not in request.files:
            flash('Không tìm thấy file', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        
        # Check if file is selected
        if file.filename == '':
            flash('Không có file được chọn', 'danger')
            return redirect(request.url)
        
        # Check file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Chỉ chấp nhận file Excel (.xlsx, .xls)', 'danger')
            return redirect(request.url)
        
        # Save file to temp directory
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(file_path)
        
        # Process file
        success_count, error_count, errors = process_student_import(file_path)
        
        # Delete temp file
        os.unlink(file_path)
        
        # Show results
        if success_count > 0:
            flash(f'Đã nhập thành công {success_count} học sinh.', 'success')
            
        if error_count > 0:
            flash(f'Có {error_count} lỗi trong quá trình nhập.', 'warning')
            for error in errors:
                flash(error, 'danger')
        
        if success_count == 0 and error_count == 0:
            flash('Không có học sinh nào được nhập.', 'warning')
        
        return redirect(url_for('students.index'))
    
    return render_template('import_data/import_students.html')

@import_bp.route('/teachers', methods=['GET', 'POST'])
@login_required
def import_teachers():
    """Nhập danh sách giáo viên từ file Excel"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập tính năng này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'excel_file' not in request.files:
            flash('Không tìm thấy file', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        
        # Check if file is selected
        if file.filename == '':
            flash('Không có file được chọn', 'danger')
            return redirect(request.url)
        
        # Check file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Chỉ chấp nhận file Excel (.xlsx, .xls)', 'danger')
            return redirect(request.url)
        
        # Save file to temp directory
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(file_path)
        
        # Process file
        success_count, error_count, errors = process_teacher_import(file_path)
        
        # Delete temp file
        os.unlink(file_path)
        
        # Show results
        if success_count > 0:
            flash(f'Đã nhập thành công {success_count} giáo viên.', 'success')
            
        if error_count > 0:
            flash(f'Có {error_count} lỗi trong quá trình nhập.', 'warning')
            for error in errors:
                flash(error, 'danger')
        
        if success_count == 0 and error_count == 0:
            flash('Không có giáo viên nào được nhập.', 'warning')
        
        return redirect(url_for('auth.users'))
    
    return render_template('import_data/import_teachers.html')

@import_bp.route('/download-template/students')
@login_required
def download_student_template():
    """Tải xuống mẫu Excel cho nhập học sinh"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập tính năng này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Create Excel template
    wb = create_student_template()
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, 'student_import_template.xlsx')
    wb.save(file_path)
    
    return send_file(file_path, as_attachment=True, download_name='student_import_template.xlsx')

@import_bp.route('/download-template/teachers')
@login_required
def download_teacher_template():
    """Tải xuống mẫu Excel cho nhập giáo viên"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập tính năng này.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Create Excel template
    wb = create_teacher_template()
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, 'teacher_import_template.xlsx')
    wb.save(file_path)
    
    return send_file(file_path, as_attachment=True, download_name='teacher_import_template.xlsx')