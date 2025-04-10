from sqlalchemy import create_engine, text
import os

# Tạo kết nối tới cơ sở dữ liệu
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Danh sách các câu lệnh SQL để tạo các cột mới trong bảng user
sql_statements = [
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS teaching_rate FLOAT DEFAULT 0.0;",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS late_fee FLOAT DEFAULT 0.0;",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS absence_fee FLOAT DEFAULT 0.0;",
    
    # Tạo bảng TeacherClassSession
    """
    CREATE TABLE IF NOT EXISTS teacher_class_session (
        id SERIAL PRIMARY KEY,
        teacher_id INTEGER NOT NULL REFERENCES "user" (id),
        course_id INTEGER NOT NULL REFERENCES course (id),
        date DATE NOT NULL DEFAULT CURRENT_DATE,
        periods INTEGER DEFAULT 1,
        note TEXT,
        CONSTRAINT unique_teacher_class_session UNIQUE (teacher_id, course_id, date)
    );
    """,
    
    # Tạo bảng TeacherSalary
    """
    CREATE TABLE IF NOT EXISTS teacher_salary (
        id SERIAL PRIMARY KEY,
        teacher_id INTEGER NOT NULL REFERENCES "user" (id),
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        total_periods INTEGER DEFAULT 0,
        base_salary FLOAT DEFAULT 0.0,
        deductions FLOAT DEFAULT 0.0,
        final_salary FLOAT DEFAULT 0.0,
        status VARCHAR(20) DEFAULT 'pending',
        payment_date TIMESTAMP,
        note TEXT,
        CONSTRAINT unique_teacher_salary UNIQUE (teacher_id, month, year)
    );
    """
]

# Thực thi các câu lệnh SQL
with engine.connect() as connection:
    for sql in sql_statements:
        connection.execute(text(sql))
        connection.commit()

print("Migration đã được áp dụng thành công!")