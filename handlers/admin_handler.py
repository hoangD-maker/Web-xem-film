import mysql.connector
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.db_helper import db_cursor
from utils.helper import admin_required, parse_and_validate_seats

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard():
    active_tab = request.args.get("tab", "overview").strip()
    search_query = request.args.get("q", "").strip()

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("""
            SELECT COUNT(*) AS total_tickets,
                   COALESCE(SUM(seat_count), 0) AS total_seats,
                   COALESCE(SUM(unit_price * seat_count + combo_price), 0) AS total_revenue
            FROM tickets
        """)
        stats = cursor.fetchone()

        cursor.execute("SELECT * FROM genres ORDER BY genre_id ASC")
        genres = cursor.fetchall()

        cursor.execute("SELECT * FROM movies ORDER BY movie_id ASC")
        movies = cursor.fetchall()

        cursor.execute("""
            SELECT s.*, m.title AS movie_title,
                   (SELECT COUNT(*) FROM booked_seats b WHERE b.showtime_id = s.showtime_id) AS booked_count
            FROM showtimes s
            JOIN movies m ON s.movie_id = m.movie_id
            ORDER BY s.show_date ASC, s.show_time ASC
        """)
        all_showtimes = cursor.fetchall()

        cursor.execute("SELECT * FROM combos ORDER BY combo_price ASC")
        combos = cursor.fetchall()

        cursor.execute("SELECT * FROM users ORDER BY user_id ASC")
        users = cursor.fetchall()

        if search_query:
            sql_tickets = """
                SELECT t.*, m.title AS movie_title,
                       s.show_date, s.show_time, s.hall_name,
                       (t.unit_price * t.seat_count + t.combo_price) AS total_amount
                FROM tickets t
                JOIN movies m ON t.movie_id = m.movie_id
                JOIN showtimes s ON t.showtime_id = s.showtime_id
                WHERE t.ticket_code LIKE %s
                   OR t.customer_name LIKE %s
                   OR t.customer_phone LIKE %s
                   OR m.title LIKE %s
                   OR t.seats_text LIKE %s
                ORDER BY t.ticket_id DESC
            """
            like_val = f"%{search_query}%"
            cursor.execute(sql_tickets, (like_val, like_val, like_val, like_val, like_val))
        else:
            cursor.execute("""
                SELECT t.*, m.title AS movie_title,
                       s.show_date, s.show_time, s.hall_name,
                       (t.unit_price * t.seat_count + t.combo_price) AS total_amount
                FROM tickets t
                JOIN movies m ON t.movie_id = m.movie_id
                JOIN showtimes s ON t.showtime_id = s.showtime_id
                ORDER BY t.ticket_id DESC
            """)
        tickets = cursor.fetchall()

    return render_template(
        "admin.html",
        active_tab=active_tab,
        stats=stats,
        genres=genres,
        movies=movies,
        all_showtimes=all_showtimes,
        combos=combos,
        tickets=tickets,
        users=users,
        search_query=search_query
    )


# --- QUẢN LÝ VÉ & GHẾ ---
@admin_bp.route("/update_ticket/<int:ticket_id>", methods=["POST"])
@admin_required
def update_ticket(ticket_id):
    customer_name = request.form.get("customer_name", "").strip()
    customer_phone = request.form.get("customer_phone", "").strip()
    cinema_name = request.form.get("cinema_name", "").strip()
    seats_raw = request.form.get("seats_text", "")
    unit_price = float(request.form.get("unit_price", 65000) or 65000)
    combo_name = request.form.get("combo_name", "Không dùng Combo").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    payment_method = request.form.get("payment_method", "Chuyển khoản QR").strip()
    payment_status = request.form.get("payment_status", "Đã thanh toán").strip()

    seat_list = parse_and_validate_seats(seats_raw)
    if not seat_list:
        flash("Danh sách ghế không hợp lệ! Vui lòng nhập mã ghế từ A1 đến H12.", "error")
        return redirect(url_for("admin.admin_dashboard", tab="tickets"))

    try:
        with db_cursor(dictionary=True, commit=True) as (_, cursor):
            cursor.execute("SELECT movie_id, showtime_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
            tk = cursor.fetchone()
            if tk:
                cursor.execute("DELETE FROM booked_seats WHERE ticket_id = %s", (ticket_id,))
                for s in seat_list:
                    cursor.execute(
                        "INSERT INTO booked_seats (ticket_id, showtime_id, movie_id, seat_code) VALUES (%s, %s, %s, %s)",
                        (ticket_id, tk["showtime_id"], tk["movie_id"], s)
                    )
                cursor.execute("""
                    UPDATE tickets
                    SET customer_name = %s, customer_phone = %s, cinema_name = %s,
                        seats_text = %s, seat_count = %s, unit_price = %s,
                        combo_name = %s, combo_price = %s, payment_method = %s, payment_status = %s
                    WHERE ticket_id = %s
                """, (
                    customer_name, customer_phone, cinema_name,
                    ", ".join(seat_list), len(seat_list), unit_price,
                    combo_name, combo_price, payment_method, payment_status, ticket_id
                ))
                flash("Đã cập nhật thông tin vé và sơ đồ ghế thành công!", "success")
    except mysql.connector.IntegrityError:
        flash("Không thể đổi sang ghế đã có người khác đặt trong cùng suất chiếu!", "error")

    return redirect(url_for("admin.admin_dashboard", tab="tickets"))


@admin_bp.route("/delete_ticket/<int:ticket_id>", methods=["GET"])
@admin_required
def delete_ticket(ticket_id):
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
    flash("Đã hủy vé và giải phóng ghế trống trên sơ đồ suất chiếu.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="tickets"))


# --- QUẢN LÝ DANH MỤC PHIM ---
@admin_bp.route("/add_movie", methods=["POST"])
@admin_required
def add_movie():
    title = request.form.get("title", "").strip()
    director = request.form.get("director", "").strip()
    actors = request.form.get("actors", "Đang cập nhật").strip()
    genre = request.form.get("genre", "").strip()
    age_rating = request.form.get("age_rating", "T16").strip()
    duration = request.form.get("duration", "120 phút").strip()
    rating_score = float(request.form.get("rating_score", 9.0) or 9.0)
    status_tab = request.form.get("status_tab", "showing").strip()
    is_hot = 1 if request.form.get("is_hot") == "1" else 0
    release_date = request.form.get("release_date", "2026-11-05").strip()
    end_date = request.form.get("end_date", "2026-12-31").strip()
    description = request.form.get("description", "").strip()
    poster_url = request.form.get("poster_url", "").strip() or "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=600&q=80"
    quote = request.form.get("quote", "").strip() or f"Trải nghiệm siêu phẩm {title} tại Beta Cine+!"
    video_url = request.form.get("video_url", "").strip() or "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"

    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("""
            INSERT INTO movies (
                title, director, actors, genre, age_rating, duration, rating_score,
                status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            title, director, actors, genre, age_rating, duration, rating_score,
            status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url
        ))
        new_movie_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price) VALUES
            (%s, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', %s, '19:30', 50000),
            (%s, 'Beta Mỹ Đình', 'Phòng 02 • IMAX Laser 3D', %s, '21:15', 55000)
        """, (new_movie_id, release_date, new_movie_id, release_date))

    flash(f"Đã thêm phim '{title}' kèm 2 suất chiếu khởi tạo thành công!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="movies"))


@admin_bp.route("/update_movie/<int:movie_id>", methods=["POST"])
@admin_required
def update_movie(movie_id):
    title = request.form.get("title", "").strip()
    director = request.form.get("director", "").strip()
    actors = request.form.get("actors", "").strip()
    genre = request.form.get("genre", "").strip()
    age_rating = request.form.get("age_rating", "T16").strip()
    duration = request.form.get("duration", "").strip()
    rating_score = float(request.form.get("rating_score", 9.0) or 9.0)
    status_tab = request.form.get("status_tab", "showing").strip()
    is_hot = 1 if request.form.get("is_hot") == "1" else 0
    release_date = request.form.get("release_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    description = request.form.get("description", "").strip()
    poster_url = request.form.get("poster_url", "").strip()
    quote = request.form.get("quote", "").strip()
    video_url = request.form.get("video_url", "").strip()

    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("""
            UPDATE movies
            SET title = %s, director = %s, actors = %s, genre = %s, age_rating = %s,
                duration = %s, rating_score = %s, status_tab = %s, is_hot = %s,
                release_date = %s, end_date = %s, description = %s,
                poster_url = %s, quote = %s, video_url = %s
            WHERE movie_id = %s
        """, (
            title, director, actors, genre, age_rating, duration, rating_score,
            status_tab, is_hot, release_date, end_date, description,
            poster_url, quote, video_url, movie_id
        ))

    flash(f"Đã cập nhật thông tin phim '{title}'!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="movies"))


@admin_bp.route("/delete_movie/<int:movie_id>", methods=["GET"])
@admin_required
def delete_movie(movie_id):
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("SELECT COUNT(*) FROM movies")
        if cursor.fetchone()[0] <= 1:
            flash("Hệ thống cần giữ lại ít nhất 1 bộ phim!", "error")
            return redirect(url_for("admin.admin_dashboard", tab="movies"))

        cursor.execute("DELETE FROM movies WHERE movie_id = %s", (movie_id,))

    flash("Đã xóa bộ phim khỏi hệ thống.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="movies"))


# --- QUẢN LÝ LỊCH CHIẾU ---
@admin_bp.route("/add_showtime", methods=["POST"])
@admin_required
def add_showtime():
    movie_id = int(request.form.get("movie_id", 1))
    cinema_name = request.form.get("cinema_name", "Beta Thanh Xuân").strip()
    hall_name = request.form.get("hall_name", "Phòng 01 • Dolby Atmos 2D").strip()
    show_date = request.form.get("show_date", "2026-11-05").strip()
    show_time = request.form.get("show_time", "20:00").strip()
    base_price = float(request.form.get("base_price", 50000) or 50000)

    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("""
            INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (movie_id, cinema_name, hall_name, show_date, show_time, base_price))

    flash(f"Đã thêm suất chiếu mới: Ngày {show_date} lúc {show_time}!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="showtimes"))


@admin_bp.route("/update_showtime/<int:showtime_id>", methods=["POST"])
@admin_required
def update_showtime(showtime_id):
    movie_id = int(request.form.get("movie_id", 1))
    cinema_name = request.form.get("cinema_name", "").strip()
    hall_name = request.form.get("hall_name", "").strip()
    show_date = request.form.get("show_date", "").strip()
    show_time = request.form.get("show_time", "").strip()
    base_price = float(request.form.get("base_price", 50000) or 50000)

    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("""
            UPDATE showtimes
            SET movie_id = %s, cinema_name = %s, hall_name = %s, show_date = %s, show_time = %s, base_price = %s
            WHERE showtime_id = %s
        """, (movie_id, cinema_name, hall_name, show_date, show_time, base_price, showtime_id))

    flash(f"Đã cập nhật suất chiếu #{showtime_id}!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="showtimes"))


@admin_bp.route("/delete_showtime/<int:showtime_id>", methods=["GET"])
@admin_required
def delete_showtime(showtime_id):
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("DELETE FROM showtimes WHERE showtime_id = %s", (showtime_id,))
    flash("Đã xóa suất chiếu.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="showtimes"))


# --- QUẢN LÝ THỂ LOẠI & COMBO ---
@admin_bp.route("/add_genre", methods=["POST"])
@admin_required
def add_genre():
    genre_name = request.form.get("genre_name", "").strip()
    if genre_name:
        try:
            with db_cursor(dictionary=False, commit=True) as (_, cursor):
                cursor.execute("INSERT INTO genres (genre_name) VALUES (%s)", (genre_name,))
            flash(f"Đã thêm thể loại '{genre_name}'!", "success")
        except mysql.connector.IntegrityError:
            flash("Thể loại này đã tồn tại!", "error")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


@admin_bp.route("/update_genre/<int:genre_id>", methods=["POST"])
@admin_required
def update_genre(genre_id):
    new_name = request.form.get("genre_name", "").strip()
    old_name = request.form.get("old_genre_name", "").strip()
    if new_name:
        try:
            with db_cursor(dictionary=False, commit=True) as (_, cursor):
                cursor.execute("UPDATE genres SET genre_name = %s WHERE genre_id = %s", (new_name, genre_id))
                if old_name and old_name != new_name:
                    cursor.execute(
                        "UPDATE movies SET genre = REPLACE(genre, %s, %s) WHERE genre LIKE %s",
                        (old_name, new_name, f"%{old_name}%")
                    )
            flash(f"Đã đổi thể loại '{old_name}' thành '{new_name}'!", "success")
        except mysql.connector.IntegrityError:
            flash("Tên thể loại bị trùng!", "error")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


@admin_bp.route("/delete_genre/<int:genre_id>", methods=["GET"])
@admin_required
def delete_genre(genre_id):
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("DELETE FROM genres WHERE genre_id = %s", (genre_id,))
    flash("Đã xóa thể loại phim.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


@admin_bp.route("/add_combo", methods=["POST"])
@admin_required
def add_combo():
    combo_name = request.form.get("combo_name", "").strip()
    combo_desc = request.form.get("combo_desc", "").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    if combo_name:
        with db_cursor(dictionary=False, commit=True) as (_, cursor):
            cursor.execute(
                "INSERT INTO combos (combo_name, combo_desc, combo_price) VALUES (%s, %s, %s)",
                (combo_name, combo_desc, combo_price)
            )
        flash(f"Đã thêm gói '{combo_name}'!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


@admin_bp.route("/update_combo/<int:combo_id>", methods=["POST"])
@admin_required
def update_combo(combo_id):
    combo_name = request.form.get("combo_name", "").strip()
    combo_desc = request.form.get("combo_desc", "").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute(
            "UPDATE combos SET combo_name = %s, combo_desc = %s, combo_price = %s WHERE combo_id = %s",
            (combo_name, combo_desc, combo_price, combo_id)
        )
    flash(f"Đã cập nhật gói '{combo_name}'!", "success")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


@admin_bp.route("/delete_combo/<int:combo_id>", methods=["GET"])
@admin_required
def delete_combo(combo_id):
    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("DELETE FROM combos WHERE combo_id = %s", (combo_id,))
    flash("Đã xóa gói Combo.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="settings"))


# --- QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG ---
@admin_bp.route("/add_user", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "123456").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    role = request.form.get("role", "customer").strip()

    try:
        with db_cursor(dictionary=False, commit=True) as (_, cursor):
            cursor.execute(
                "INSERT INTO users (username, password, full_name, phone, role) VALUES (%s, %s, %s, %s, %s)",
                (username, password, full_name, phone, role)
            )
        flash(f"Đã tạo tài khoản '{username}' ({role}) thành công!", "success")
    except mysql.connector.IntegrityError:
        flash("Tên đăng nhập đã tồn tại!", "error")
    return redirect(url_for("admin.admin_dashboard", tab="users"))


@admin_bp.route("/delete_user/<int:user_id>", methods=["GET"])
@admin_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("Không thể tự xóa tài khoản đang đăng nhập!", "error")
        return redirect(url_for("admin.admin_dashboard", tab="users"))

    with db_cursor(dictionary=False, commit=True) as (_, cursor):
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    flash("Đã xóa tài khoản người dùng.", "success")
    return redirect(url_for("admin.admin_dashboard", tab="users"))
