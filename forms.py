from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, DecimalField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from datetime import date

class LoginForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired()])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember_me = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')

class UserForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mật khẩu', validators=[Optional(), Length(min=6)])
    full_name = StringField('Họ và tên', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Số điện thoại', validators=[Optional(), Length(max=20)])
    role = SelectField('Vai trò', choices=[
        ('teacher', 'Giáo viên'),
        ('admin', 'Quản trị viên'),
        ('sadmin', 'Quản trị viên cấp cao')
    ], validators=[DataRequired()])
    active = BooleanField('Đang hoạt động', default=True)
    submit = SubmitField('Lưu')

class StudentForm(FlaskForm):
    full_name = StringField('Họ và tên', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Số điện thoại', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Ngày sinh', validators=[Optional()])
    address = StringField('Địa chỉ', validators=[Optional(), Length(max=200)])
    parent_name = StringField('Họ tên phụ huynh', validators=[Optional(), Length(max=100)])
    parent_phone = StringField('Số điện thoại phụ huynh', validators=[Optional(), Length(max=20)])
    active = BooleanField('Đang hoạt động', default=True)
    submit = SubmitField('Lưu')

class CourseForm(FlaskForm):
    name = StringField('Tên khóa học', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    teacher_id = SelectField('Giáo viên', coerce=int, validators=[DataRequired()])
    start_date = DateField('Ngày bắt đầu', validators=[DataRequired()])
    end_date = DateField('Ngày kết thúc', validators=[DataRequired()])
    schedule = StringField('Lịch học', validators=[Optional(), Length(max=200)])
    max_students = IntegerField('Số học sinh tối đa', validators=[Optional(), NumberRange(min=1)])
    fee = DecimalField('Học phí', validators=[Optional(), NumberRange(min=0)])
    session_fee = DecimalField('Phí mỗi buổi dạy', validators=[Optional(), NumberRange(min=0)])
    active = BooleanField('Đang hoạt động', default=True)
    submit = SubmitField('Lưu')
    
    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('Ngày kết thúc phải sau ngày bắt đầu.')

class EnrollmentForm(FlaskForm):
    student_id = SelectField('Học sinh', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Khóa học', coerce=int, validators=[DataRequired()])
    enrollment_date = DateField('Ngày đăng ký', validators=[Optional()], default=date.today)
    fee_paid = DecimalField('Học phí đã đóng', validators=[Optional(), NumberRange(min=0)], default=0)
    payment_status = SelectField('Trạng thái thanh toán', choices=[
        ('pending', 'Chưa thanh toán'),
        ('partial', 'Thanh toán một phần'),
        ('paid', 'Đã thanh toán')
    ], validators=[DataRequired()])
    payment_date = DateField('Ngày thanh toán', validators=[Optional()])
    submit = SubmitField('Lưu')

class StudentAttendanceForm(FlaskForm):
    status = SelectField('Trạng thái', choices=[
        ('present', 'Có mặt'),
        ('absent', 'Vắng mặt'),
        ('late', 'Đi muộn')
    ], validators=[DataRequired()])
    remark = TextAreaField('Ghi chú', validators=[Optional()])
    submit = SubmitField('Lưu')

class TeacherAttendanceForm(FlaskForm):
    status = SelectField('Trạng thái', choices=[
        ('present', 'Có mặt'),
        ('absent', 'Vắng mặt'),
        ('late', 'Đi muộn')
    ], validators=[DataRequired()])
    remark = TextAreaField('Ghi chú', validators=[Optional()])
    submit = SubmitField('Lưu')

class TeacherSalaryForm(FlaskForm):
    teacher_id = SelectField('Giáo viên', coerce=int, validators=[DataRequired()])
    month = SelectField('Tháng', coerce=int, choices=[
        (1, 'Tháng 1'), (2, 'Tháng 2'), (3, 'Tháng 3'),
        (4, 'Tháng 4'), (5, 'Tháng 5'), (6, 'Tháng 6'),
        (7, 'Tháng 7'), (8, 'Tháng 8'), (9, 'Tháng 9'),
        (10, 'Tháng 10'), (11, 'Tháng 11'), (12, 'Tháng 12')
    ], validators=[DataRequired()])
    year = IntegerField('Năm', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    amount = DecimalField('Số tiền', validators=[DataRequired(), NumberRange(min=0)])
    payment_date = DateField('Ngày thanh toán', validators=[Optional()])
    payment_status = SelectField('Trạng thái thanh toán', choices=[
        ('pending', 'Chưa thanh toán'),
        ('paid', 'Đã thanh toán')
    ], validators=[DataRequired()])
    remark = TextAreaField('Ghi chú', validators=[Optional()])
    submit = SubmitField('Lưu')

class AssessmentForm(FlaskForm):
    student_id = SelectField('Học sinh', coerce=int, validators=[DataRequired()])
    date = DateField('Ngày đánh giá', validators=[Optional()], default=date.today)
    content = TextAreaField('Nội dung đánh giá', validators=[DataRequired()])
    send_email = BooleanField('Gửi email thông báo', default=True)
    submit = SubmitField('Lưu')

class MessageForm(FlaskForm):
    recipient_id = SelectField('Người nhận', coerce=int, validators=[DataRequired()])
    subject = StringField('Tiêu đề', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Nội dung', validators=[DataRequired()])
    submit = SubmitField('Gửi')

class SearchForm(FlaskForm):
    search = StringField('Tìm kiếm', validators=[Optional()])
    submit = SubmitField('Tìm')
