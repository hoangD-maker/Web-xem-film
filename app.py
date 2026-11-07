"""
File cầu nối (Entry-point Bridge) giúp lệnh mặc định trên Render (gunicorn app:app)
hoặc lệnh `python app.py` hoạt động tương thích 100% với cấu trúc mới trong `main.py`.
"""
from main import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
