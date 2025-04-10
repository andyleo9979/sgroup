import logging
from flask import render_template_string
from datetime import datetime
from app import mail
from flask_mail import Message

def send_receipt_email(recipient_email, receipt_number, amount, course_name, student_name):
    """
    Send a payment receipt email to a student.
    
    Args:
        recipient_email: The email address of the recipient
        receipt_number: The unique receipt number
        amount: The payment amount
        course_name: The name of the course
        student_name: The student's full name
    """
    try:
        subject = f"Payment Receipt #{receipt_number}"
        
        # Email template
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .header { background-color: #4285f4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; }
                .content { padding: 20px; }
                .footer { font-size: 12px; text-align: center; margin-top: 20px; color: #777; }
                .receipt-info { margin: 15px 0; }
                .receipt-info div { margin: 5px 0; }
                .amount { font-size: 24px; font-weight: bold; color: #4285f4; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Biên lai thanh toán</h2>
                </div>
                <div class="content">
                    <p>Dear {{ student_name }},</p>
                    <p>Cảm ơn bạn đã thanh toán. Sgroup xin gửi biên lai của bạn:</p>
                    
                    <div class="receipt-info">
                        <div>Số biên nhận: <strong>{{ receipt_number }}</strong></div>
                        <div>Khóa học: <strong>{{ course_name }}</strong></div>
                        <div>Số tiền đã thanh toán: <span class="amount">${{ amount }}</span></div>
                        <div>Ngày: <strong>{{ date }}</strong></div>
                    </div>
                    
                    <p>
Nếu bạn có bất kỳ câu hỏi nào về khoản thanh toán này, vui lòng liên hệ với chúng tôi.</p>
                    
                    <p>Trân trọng,<br>Trung tâm Sgroup</p>
                </div>
                <div class="footer">
                    
Đây là email tự động. Vui lòng không trả lời email này.
                </div>
            </div>
        </body>
        </html>
        """
        
        # Render the template with variables
        html = render_template_string(
            template,
            student_name=student_name,
            receipt_number=receipt_number,
            course_name=course_name,
            amount="{:.2f}".format(amount),
            date=datetime.now().strftime("%B %d, %Y")
        )
        
        # Create the message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=html
        )
        
        # Send the email
        mail.send(msg)
        logging.info(f"Email biên lai đã được gửi đến {recipient_email}")
    except Exception as e:
        logging.error(f"Không gửi được email biên lai: {str(e)}")
        raise


def send_notification_email(recipient_email, title, message):
    """
    Gửi email thông báo tới người dùng.
    
    Args:
        recipient_email: Địa chỉ email của người nhận
        title: Tiêu đề thông báo
        message: Tin nhắn thông báo
    """
    try:
        subject = f"Thông báo của Trung tâm Đào tạo Sgroup: {title}"
        
        # Email template
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .header { background-color: #4285f4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; }
                .content { padding: 20px; }
                .footer { font-size: 12px; text-align: center; margin-top: 20px; color: #777; }
                .title { font-size: 20px; font-weight: bold; margin-bottom: 15px; }
                .message { line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Trung tâm Đào tạo Sgroup</h2>
                </div>
                <div class="content">
                    <div class="title">{{ title }}</div>
                    <div class="message">{{ message }}</div>
                    
                    <p style="margin-top: 20px;">Trân trọng,<br>Xin cảm ơn</p>
                </div>
                <div class="footer">
                    Đây là email tự động. Vui lòng không trả lời email này.
                </div>
            </div>
        </body>
        </html>
        """
        
        # Render the template with variables
        html = render_template_string(
            template,
            title=title,
            message=message
        )
        
        # Create the message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=html
        )
        
        # Send the email
        mail.send(msg)
        logging.info(f"Email thông báo được gửi tới {recipient_email}")
    except Exception as e:
        logging.error(f"Không gửi được email thông báo: {str(e)}")
        raise
def send_attendance_email(student_email, student_name, course_name, date, status, had_meal):
    """Gửi email thông báo điểm danh cho học sinh"""
    subject = f"Thông báo điểm danh - {course_name}"
    
    # Email template
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .header { background-color: #4285f4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; }
            .content { padding: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Thông báo điểm danh</h2>
            </div>
            <div class="content">
                <p>Xin chào {{ student_name }},</p>
                <p>Bạn đã được điểm danh cho khóa học <strong>{{ course_name }}</strong> ngày {{ date.strftime('%d/%m/%Y') }}:</p>
                <ul>
                    <li>Trạng thái: <strong>{{ "Có mặt" if status == "present" else "Vắng mặt" if status == "absent" else "Đi muộn" }}</strong></li>
                    <li>Ăn tại trung tâm: <strong>{{ "Có" if had_meal else "Không" }}</strong></li>
                </ul>
                <p>Trân trọng,<br>Trung tâm Sgroup</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    html = render_template_string(
        template,
        student_name=student_name,
        course_name=course_name,
        date=date,
        status=status,
        had_meal=had_meal
    )
    
    msg = Message(
        subject=subject,
        recipients=[student_email],
        html=html
    )
    
    mail.send(msg)

def send_comment_email(student_email, student_name, course_name, date, comment, teacher_name):
    """Gửi email thông báo nhận xét buổi học"""
    subject = f"Nhận xét buổi học - {course_name}"
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .header { background-color: #4285f4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; }
            .content { padding: 20px; }
            .comment { background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Nhận xét buổi học</h2>
            </div>
            <div class="content">
                <p>Xin chào {{ student_name }},</p>
                <p>Giáo viên {{ teacher_name }} đã nhận xét về buổi học {{ course_name }} ngày {{ date.strftime('%d/%m/%Y') }}:</p>
                <div class="comment">
                    {{ comment }}
                </div>
                <p>Trân trọng,<br>Trung tâm Sgroup</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    html = render_template_string(
        template,
        student_name=student_name,
        course_name=course_name,
        date=date,
        comment=comment,
        teacher_name=teacher_name
    )
    
    msg = Message(
        subject=subject,
        recipients=[student_email],
        html=html
    )
    
    mail.send(msg)
