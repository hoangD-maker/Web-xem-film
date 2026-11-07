import mysql.connector
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.db_helper import db_cursor
from utils.helper import is_valid_phone

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def root():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("customer.customer_home"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute(
                "SELECT * FROM users WHERE username = %s AND password = %s",
                (username, password)
            )
            user = cursor.fetchone()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["phone"] = user["phone"]
            session["role"] = user["role"]
            role_label = "Quản trị viên" if user["role"] == "admin" else "Khách hàng"
            flash(f"Xin chào {user['full_name']}! Bạn đã đăng nhập với quyền {role_label}.", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            return redirect(url_for("customer.customer_home"))

        flash("Sai tên đăng nhập hoặc mật khẩu! Vui lòng kiểm tra lại.", "error")

    return render_template("login.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not username or not password or not full_name:
        flash("Vui lòng điền đầy đủ thông tin đăng ký!", "error")
        return redirect(url_for("auth.login"))

    if not is_valid_phone(phone):
        flash("Số điện thoại không hợp lệ (cần bắt đầu bằng số 0 và gồm 9-11 chữ số)!", "error")
        return redirect(url_for("auth.login"))

    try:
        with db_cursor(dictionary=True, commit=True) as (_, cursor):
            cursor.execute(
                "INSERT INTO users (username, password, full_name, phone, role) VALUES (%s, %s, %s, %s, 'customer')",
                (username, password, full_name, phone)
            )
            new_id = cursor.lastrowid

        session["user_id"] = new_id
        session["username"] = username
        session["full_name"] = full_name
        session["phone"] = phone
        session["role"] = "customer"
        flash(f"Đăng ký thành công! Chào mừng {full_name} đến với Beta Cine+.", "success")
        return redirect(url_for("customer.customer_home"))

    except mysql.connector.IntegrityError:
        flash(f"Tên tài khoản '{username}' đã có người sử dụng!", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất khỏi hệ thống.", "success")
    return redirect(url_for("auth.login"))
