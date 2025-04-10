
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Kiểm tra xem bảng message đã tồn tại chưa
        db.session.execute(text("SELECT id FROM message LIMIT 1"))
        print("Bảng message đã tồn tại.")
    except Exception:
        try:
            # Tạo bảng message
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS message (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL REFERENCES "user" (id),
                    recipient_id INTEGER NOT NULL REFERENCES "user" (id),
                    content TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            print("Đã tạo bảng message thành công.")
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi tạo bảng message: {str(e)}")
