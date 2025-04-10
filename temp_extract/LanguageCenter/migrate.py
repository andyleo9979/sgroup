
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Kiểm tra xem cột comment đã tồn tại chưa
        db.session.execute(text("SELECT comment FROM attendance LIMIT 1"))
        print("Cột comment đã tồn tại trong bảng attendance.")
    except Exception:
        try:
            # Thêm cột comment vào bảng attendance
            db.session.execute(text("ALTER TABLE attendance ADD COLUMN comment TEXT"))
            db.session.commit()
            print("Đã thêm cột comment vào bảng attendance thành công.")
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi thêm cột comment: {str(e)}")
