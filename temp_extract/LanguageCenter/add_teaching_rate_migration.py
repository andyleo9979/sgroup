from app import app, db
from models import Course
from sqlalchemy import text

def add_teaching_rate_column():
    """Thêm cột teaching_rate vào bảng course"""
    with app.app_context():
        try:
            # Kiểm tra xem cột teaching_rate đã tồn tại chưa
            db.session.execute(text('SELECT teaching_rate FROM course LIMIT 1'))
            print("Cột teaching_rate đã tồn tại. Không cần thêm mới.")
            return
        except Exception:
            # Cột chưa tồn tại, thêm mới
            db.session.execute(text('ALTER TABLE course ADD COLUMN teaching_rate FLOAT DEFAULT 0.0'))
            db.session.commit()
            print("Đã thêm cột teaching_rate vào bảng course thành công.")

if __name__ == '__main__':
    add_teaching_rate_column()