import os
from flask import Flask
from dotenv import load_dotenv

from handlers.auth_handler import auth_bp
from handlers.customer_handler import customer_bp
from handlers.admin_handler import admin_bp

load_dotenv()


def create_app() -> Flask:
    """Khởi tạo ứng dụng Flask và đăng ký các Blueprint điều hướng."""
    application = Flask(__name__)
    application.secret_key = os.getenv("FLASK_SECRET_KEY", "betacine_secret_2026")
    application.config["TEMPLATES_AUTO_RELOAD"] = True

    # Đăng ký 3 module xử lý nghiệp vụ
    application.register_blueprint(auth_bp)
    application.register_blueprint(customer_bp)
    application.register_blueprint(admin_bp)

    return application


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
