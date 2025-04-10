
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask_sqlalchemy import SQLAlchemy

scheduler = BackgroundScheduler()

def init_scheduler(db: SQLAlchemy):
    """Khởi tạo scheduler với database dependency được inject"""
    from models import Attendance, Notification, User, Course, Enrollment
    from datetime import datetime, timedelta
    
    def send_daily_attendance_notifications():
        """Gửi thông báo tổng kết điểm danh cuối ngày"""
        # Lấy tất cả giáo viên
        teachers = User.query.filter_by(role='teacher').all()
        
        for teacher in teachers:
            # Lấy các điểm danh có ghi chú từ giáo viên này
            attendances = Attendance.query.filter(
                Attendance.recorded_by == teacher.id,
                Attendance.comment.isnot(None)
            ).all()
            
            if attendances:
                # Tạo nội dung thông báo
                message = "Tổng kết điểm danh và nhận xét học sinh hôm nay:\n\n"
                for attendance in attendances:
                    message += f"- Học sinh {attendance.student.full_name} ({attendance.course.name}): {attendance.comment}\n"
                
                # Tạo thông báo mới
                notification = Notification(
                    recipient_id=teacher.id,
                    title="Tổng kết điểm danh ngày",
                    message=message,
                    notification_type="info"
                )
                
                db.session.add(notification)
        
        db.session.commit()

    # Đăng ký job gửi thông báo vào 22h hàng ngày
    def check_course_completion():
        """Kiểm tra và gửi thông báo về các khóa học sắp kết thúc"""
        # Lấy danh sách admin
        admins = User.query.filter_by(role='admin').all()
        
        # Lấy các khóa học đang hoạt động
        active_courses = Course.query.filter_by(active=True).all()
        
        for course in active_courses:
            remaining = course.remaining_sessions()
            if remaining <= 3 and remaining > 0:
                # Lấy danh sách học sinh đang học
                enrollments = Enrollment.query.filter_by(course_id=course.id, status='active').all()
                if not enrollments:
                    continue
                    
                # Tạo nội dung thông báo
                student_list = "\n".join([f"- {e.student.full_name}" for e in enrollments])
                message = f"""Khóa học {course.name} sắp kết thúc (còn {remaining} buổi):
                
Danh sách học sinh:
{student_list}

Vui lòng kiểm tra và liên hệ với phụ huynh về việc đăng ký khóa học tiếp theo."""

                # Gửi thông báo cho mỗi admin
                for admin in admins:
                    notification = Notification(
                        recipient_id=admin.id,
                        title=f"Thông báo: Khóa học {course.name} sắp kết thúc",
                        message=message,
                        notification_type="warning"
                    )
                    db.session.add(notification)
                    
        db.session.commit()

    # Đăng ký các jobs
    scheduler.add_job(
        send_daily_attendance_notifications,
        trigger=CronTrigger(hour=22),
        id='daily_attendance_notifications',
        replace_existing=True
    )
    
    scheduler.add_job(
        check_course_completion,
        trigger=CronTrigger(hour=8),  # Chạy lúc 8 giờ sáng mỗi ngày
        id='check_course_completion',
        replace_existing=True
    )
    
    scheduler.start()
