import os
from contextlib import contextmanager
import mysql.connector


def get_db_connection():
    """Khởi tạo kết nối tới cơ sở dữ liệu MySQL / TiDB Cloud từ biến môi trường."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "beta_cinema_db"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    )


@contextmanager
def db_cursor(dictionary=True, commit=False):
    """
    Context Manager quản lý vòng đời kết nối và con trỏ (cursor) tự động.
    - Tự động commit nếu commit=True và không có lỗi.
    - Tự động rollback nếu xảy ra ngoại lệ (Exception).
    - Luôn đóng cursor và connection trong khối finally (chống rò rỉ kết nối).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
