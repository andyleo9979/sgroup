from datetime import datetime, time
from app import db
from flask_login import UserMixin
from sqlalchemy import func


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='teacher')  # sadmin, admin or teacher
    # Đơn giá tiết giảng dạy (VND/tiết)
    teaching_rate = db.Column(db.Float, default=0.0)
    # Phí trừ khi đi muộn (VND/lần)
    late_fee = db.Column(db.Float, default=0.0)
    # Phí trừ khi vắng mặt không phép (VND/lần)
    absence_fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
        
    def calculate_salary(self, month, year):
        """Tính lương cho giáo viên dựa trên số tiết dạy và tình trạng chấm công"""
        from sqlalchemy import extract
        
        # Trường hợp chưa cài đặt đơn giá dạy
        if not self.teaching_rate:
            return 0
            
        # Lấy tất cả buổi dạy trong tháng
        teaching_sessions = TeacherClassSession.query.filter(
            TeacherClassSession.teacher_id == self.id,
            extract('month', TeacherClassSession.date) == month,
            extract('year', TeacherClassSession.date) == year
        ).all()
        
        # Tính tổng số tiết dạy
        total_periods = sum(session.periods for session in teaching_sessions)
        
        # Tính tổng thu nhập từ giảng dạy
        total_earning = total_periods * self.teaching_rate
        
        # Lấy tất cả điểm danh trong tháng
        attendances = TeacherAttendance.query.filter(
            TeacherAttendance.teacher_id == self.id,
            extract('month', TeacherAttendance.date) == month,
            extract('year', TeacherAttendance.date) == year
        ).all()
        
        # Tính khấu trừ
        deductions = 0
        for attendance in attendances:
            if attendance.status == 'absent':
                deductions += self.absence_fee
            elif attendance.status == 'late':
                deductions += self.late_fee
                
        # Tổng lương = thu nhập - khấu trừ
        final_salary = total_earning - deductions
        
        return max(0, final_salary)  # Đảm bảo lương không âm


# Định nghĩa trước lớp Attendance để tránh lỗi tham chiếu vòng tròn
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    status = db.Column(db.String(10), default='present')  # present, absent, late
    had_meal = db.Column(db.Boolean, default=False)  # Đánh dấu học sinh có ăn tại trung tâm hay không
    note = db.Column(db.Text)  # Ghi chú thêm (nếu cần)
    comment = db.Column(db.Text)  # Nhận xét cuối buổi học
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    recorder = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'date', name='unique_attendance'),
    )
    
    def __repr__(self):
        return f'<Điểm danh {self.date}>'
        

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    date_of_birth = db.Column(db.Date)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    # Trạng thái bán trú
    boarding_status = db.Column(db.String(20), default='không')  # không, bán trú, nội trú
    meal_fee_per_day = db.Column(db.Float, default=0.0)  # Phí ăn mỗi ngày
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, cascade="all, delete-orphan")
    payments = db.relationship('Payment', backref='student', lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Học sinh {self.last_name} {self.first_name}>'
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
    
    @property
    def total_paid(self):
        return sum(payment.amount for payment in self.payments)
    
    @property
    def total_courses(self):
        return len(self.enrollments)
    
    def total_attendances(self, course_id=None):
        """Đếm tổng số buổi đã tham gia"""
        if course_id:
            return len([a for a in self.attendances if a.course_id == course_id])
        return len(self.attendances)
    
    def total_meal_fee(self, month=None, year=None):
        """Tính tổng phí ăn dựa trên số ngày có mặt và ăn tại trung tâm"""
        if self.boarding_status == 'không':
            return 0
            
        if month and year:
            # Lọc theo tháng và năm cụ thể
            start_date = datetime(year, month, 1).date()
            
            # Tính ngày cuối cùng của tháng
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month + 1, 1).date()
            
            # Đếm số ngày có mặt và ăn    
            meal_count = len([a for a in self.attendances if a.had_meal and a.date >= start_date and a.date < end_date])
        else:
            # Đếm tất cả ngày có ăn
            meal_count = len([a for a in self.attendances if a.had_meal])
            
        return meal_count * self.meal_fee_per_day


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False)
    max_students = db.Column(db.Integer, default=20)
    active = db.Column(db.Boolean, default=True)
    total_sessions = db.Column(db.Integer, default=0)  # Tổng số buổi học dự kiến
    teaching_rate = db.Column(db.Float, default=0.0)  # Đơn giá tiết dạy cho khóa học này
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='course', lazy=True, cascade="all, delete-orphan")
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher = db.relationship('User', backref='courses')
    
    def __repr__(self):
        return f'<Khóa học {self.name}>'
    
    @property
    def enrolled_students_count(self):
        return len(self.enrollments)
    
    @property
    def is_full(self):
        return self.enrolled_students_count >= self.max_students
    
    def completed_sessions(self):
        """Đếm số buổi học đã hoàn thành dựa trên ngày điểm danh duy nhất"""
        # Lấy tất cả các ngày duy nhất có điểm danh cho khóa học này
        unique_dates = set(a.date for a in self.attendances)
        return len(unique_dates)
    
    def remaining_sessions(self):
        """Tính số buổi học còn lại"""
        return max(0, self.total_sessions - self.completed_sessions())


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, completed, dropped
    
    def __repr__(self):
        return f'<Tuyển sinh {self.student_id} vào khóa học {self.course_id}>'


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    course = db.relationship('Course')
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), default='cash')  # cash, card, transfer
    receipt_number = db.Column(db.String(50), nullable=False, unique=True)
    payment_type = db.Column(db.String(20), default='tuition')  # tuition, meal, other
    
    def __repr__(self):
        return f'<Thanh toán {self.receipt_number} - {self.amount}>'


class TeacherAttendance(db.Model):
    """Bảng lưu thông tin chấm công giáo viên"""
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    time_in = db.Column(db.Time, nullable=True)
    time_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), default='present') # present, absent, late, leave
    note = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='attendances')
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'date', name='unique_teacher_attendance'),
    )
    
    def __repr__(self):
        return f'<TeacherAttendance {self.teacher.username} on {self.date}>'
    
    @property
    def working_hours(self):
        """Tính số giờ làm việc trong ngày"""
        if not self.time_in or not self.time_out:
            return 0
            
        time_in_seconds = self.time_in.hour * 3600 + self.time_in.minute * 60 + self.time_in.second
        time_out_seconds = self.time_out.hour * 3600 + self.time_out.minute * 60 + self.time_out.second
        
        if time_out_seconds < time_in_seconds:  # Trường hợp ra về vào ngày hôm sau
            time_out_seconds += 24 * 3600
            
        work_seconds = time_out_seconds - time_in_seconds
        return round(work_seconds / 3600, 2)  # Trả về số giờ làm việc (làm tròn 2 chữ số)
    
    @property
    def formatted_time_in(self):
        """Trả về thời gian vào định dạng HH:MM"""
        return self.time_in.strftime("%H:%M") if self.time_in else "--:--"
        
    @property
    def formatted_time_out(self):
        """Trả về thời gian ra định dạng HH:MM"""
        return self.time_out.strftime("%H:%M") if self.time_out else "--:--"


class TeacherClassSession(db.Model):
    """Bảng lưu thông tin về buổi dạy của giáo viên và số tiết giảng dạy"""
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    periods = db.Column(db.Integer, default=1)  # Số tiết giảng dạy trong buổi này
    note = db.Column(db.Text)
    
    # Relationships
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='teaching_sessions')
    course = db.relationship('Course', backref='teaching_sessions')
    
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'course_id', 'date', name='unique_teacher_class_session'),
    )
    
    def __repr__(self):
        return f'<TeacherClassSession {self.teacher.username} - {self.course.name} - {self.date}>'


class TeacherSalary(db.Model):
    """Bảng lưu thông tin lương giáo viên theo tháng"""
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_periods = db.Column(db.Integer, default=0)  # Tổng số tiết dạy
    base_salary = db.Column(db.Float, default=0.0)    # Lương cơ bản
    deductions = db.Column(db.Float, default=0.0)     # Khấu trừ
    final_salary = db.Column(db.Float, default=0.0)   # Lương thực nhận
    status = db.Column(db.String(20), default='pending')  # pending, approved, paid
    payment_date = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text)
    
    # Relationships
    teacher = db.relationship('User', backref='salary_records')
    
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'month', 'year', name='unique_teacher_salary'),
    )
    
    def __repr__(self):
        return f'<TeacherSalary {self.teacher.username} - {self.month}/{self.year}>'
        
    def calculate(self):
        """Tính lương dựa trên các dữ liệu đã có"""
        # Tính lương thực nhận
        self.final_salary = self.base_salary - self.deductions
        return self.final_salary


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient = db.relationship('User', backref='notifications')
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_type = db.Column(db.String(20), default='info')  # info, warning, success, error
    
    def __repr__(self):
        return f'<Thông báo {self.id} dành cho{self.recipient_id}>'


class Message(db.Model):
    """Bảng lưu trữ tin nhắn giữa các users"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), default='') # Tiêu đề (có thể để trống)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
    def __repr__(self):
        return f'<Message {self.id}>'

class ActivityLog(db.Model):
    """Bảng lưu trữ logs hoạt động của người dùng"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Nullable để có thể log cả khi chưa đăng nhập
    user = db.relationship('User', backref='activity_logs')
    action = db.Column(db.String(100), nullable=False) # Tên hành động
    details = db.Column(db.Text, nullable=True) # Chi tiết hành động
    ip_address = db.Column(db.String(50), nullable=True) # Địa chỉ IP
    user_agent = db.Column(db.String(255), nullable=True) # Thông tin trình duyệt
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Thời gian thực hiện
    
    def __repr__(self):
        return f'<Log {self.id}: {self.action}>'
