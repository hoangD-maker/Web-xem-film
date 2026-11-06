import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "beta_cinema_db")
        )
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tickets;")
            count = cursor.fetchone()[0]
            print(f"✅ Kết nối MySQL thành công! Hiện có {count} vé trong bảng 'tickets'.")
            cursor.close()
            conn.close()
    except Exception as e:
        print("❌ Lỗi kết nối MySQL:", e)
        print("👉 Hãy kiểm tra xem bạn đã bật MySQL và chạy file database.sql chưa!")

if __name__ == "__main__":
    test_connection()