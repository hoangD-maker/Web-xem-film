import os
import math
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "betacine_secret_2026")
# Bắt buộc Flask luôn tải lại file HTML mới nhất, không lưu cache cũ
app.config["TEMPLATES_AUTO_RELOAD"] = True

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]
COLS = list(range(1, 13))


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "beta_cinema_db"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    )


# THUẬT TOÁN TÍNH TỌA ĐỘ 3D POV NGUYÊN BẢN (ĐÃ KHÔI PHỤC ĐỦ SCREEN_SCALE, VP_OFFSET_X, VP_OFFSET_Y)
def calculate_seat_3d_pov(seat_code: str, base_price: float = 50000.0):
    seat_code = seat_code.strip().upper()
    row_char = seat_code[0] if seat_code and seat_code[0] in ROWS else "D"
    try:
        col_num = int(seat_code[1:])
        if col_num not in COLS:
            col_num = 6
    except ValueError:
        col_num = 6

    row_idx = ROWS.index(row_char)
    col_offset = col_num - 6.5

    z_dist = 4.6 + row_idx * 1.83
    y_eye = 1.60 + row_idx * 0.58
    x_lat = col_offset * 1.12
    delta_y = 4.5 - y_eye

    euclid_dist = math.sqrt(x_lat**2 + delta_y**2 + z_dist**2)
    pitch_deg = math.degrees(math.atan2(delta_y, z_dist))
    yaw_deg = math.degrees(math.atan2(x_lat, z_dist))

    visual_score = int(max(55, min(99, round(100 - abs(pitch_deg) * 1.3 - abs(yaw_deg) * 1.1))))
    audio_score = int(max(58, min(99, round(100 - math.sqrt(((row_idx - 3.5) * 4.2)**2 + (col_offset * 4.5)**2)))))

    if row_char in ["A", "B", "C"]:
        seat_type = "Ghế Thường"
        price = int(base_price)
    elif row_char in ["D", "E", "F"]:
        seat_type = "Ghế VIP"
        price = int(base_price + 15000)
    else:
        seat_type = "Ghế Đôi Sweetbox"
        price = int(base_price + 20000)

    if row_idx <= 1:
        advice = f"Ghế {row_char}{col_num} nằm sát màn hình ({euclid_dist:.1f}m), khung hình cực đại nhưng cần ngửa cổ +{pitch_deg:.0f}°."
    elif 3 <= row_idx <= 5 and abs(col_offset) <= 2.5:
        advice = f"Vị trí kim cương trong rạp! Tầm mắt thẳng tâm màn hình ({euclid_dist:.1f}m), không mỏi cổ và nằm ngay giao điểm vàng của hệ thống loa vòm Dolby Atmos 360°."
    elif row_idx >= 6:
        advice = f"Ghế đôi Sweetbox ở bậc cao nhất rạp ({euclid_dist:.1f}m), tầm nhìn bao quát toàn bộ phòng chiếu không vật cản."
    else:
        side = "trái" if col_offset < 0 else "phải"
        advice = f"Góc nhìn nghiêng {abs(yaw_deg):.0f}° từ cánh {side} (cách màn hình {euclid_dist:.1f}m), gần lối đi bậc thang."

    return {
        "seat": f"{row_char}{col_num}",
        "row": row_char,
        "row_idx": row_idx,
        "col_offset": col_offset,
        "seat_type": seat_type,
        "price": price,
        "distance_m": round(euclid_dist, 1),
        "pitch_deg": round(pitch_deg, 0),
        "yaw_deg": round(abs(yaw_deg), 0),
        "visual_score": visual_score,
        "audio_score": audio_score,
        "advice": advice,
        "screen_scale": round(1.35 - row_idx * 0.075, 3),
        "vp_offset_x": round(-col_offset * 24.0, 2),
        "vp_offset_y": round((3.2 - row_idx) * 14.0, 2),
    }


# =====================================================================
# 1. XÁC THỰC TÀI KHOẢN: ĐĂNG NHẬP, ĐĂNG KÝ & ĐĂNG XUẤT
# =====================================================================
@app.route("/", methods=["GET"])
def root():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("customer_home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["phone"] = user["phone"]
            session["role"] = user["role"]
            flash(f"Xin chào {user['full_name']}! Bạn đã đăng nhập với quyền {'Quản trị viên' if user['role'] == 'admin' else 'Khách hàng'}.", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("customer_home"))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu! Vui lòng kiểm tra lại.", "error")

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not username or not password or not full_name:
        flash("Vui lòng điền đầy đủ thông tin đăng ký!", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO users (username, password, full_name, phone, role) VALUES (%s, %s, %s, %s, 'customer')",
            (username, password, full_name, phone)
        )
        conn.commit()
        new_id = cursor.lastrowid
        session["user_id"] = new_id
        session["username"] = username
        session["full_name"] = full_name
        session["phone"] = phone
        session["role"] = "customer"
        flash(f"Đăng ký thành công! Chào mừng {full_name} đến với Beta Cine+.", "success")
        return redirect(url_for("customer_home"))
    except mysql.connector.IntegrityError:
        flash(f"Tên tài khoản '{username}' đã có người sử dụng!", "error")
        return redirect(url_for("login"))
    finally:
        cursor.close()
        conn.close()


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất khỏi hệ thống.", "success")
    return redirect(url_for("login"))


# =====================================================================
# 2. LUỒNG KHÁCH HÀNG - TRANG 1: TRANG CHỦ CHỌN PHIM & TRA CỨU VÉ (/home)
# =====================================================================
@app.route("/home", methods=["GET"])
def customer_home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search_ticket = request.args.get("q", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM genres ORDER BY genre_id ASC")
    genres = cursor.fetchall()

    cursor.execute("SELECT * FROM movies ORDER BY movie_id ASC")
    movies = cursor.fetchall()

    user_phone = session.get("phone", "")
    if search_ticket:
        cursor.execute("""
            SELECT t.*, m.title AS movie_title, s.show_date, s.show_time, s.hall_name,
                   (t.unit_price * t.seat_count + t.combo_price) AS total_amount
            FROM tickets t
            JOIN movies m ON t.movie_id = m.movie_id
            JOIN showtimes s ON t.showtime_id = s.showtime_id
            WHERE UPPER(t.ticket_code) = UPPER(%s) OR t.customer_phone = %s
            ORDER BY t.ticket_id DESC
        """, (search_ticket, search_ticket))
    else:
        cursor.execute("""
            SELECT t.*, m.title AS movie_title, s.show_date, s.show_time, s.hall_name,
                   (t.unit_price * t.seat_count + t.combo_price) AS total_amount
            FROM tickets t
            JOIN movies m ON t.movie_id = m.movie_id
            JOIN showtimes s ON t.showtime_id = s.showtime_id
            WHERE t.customer_phone = %s
            ORDER BY t.ticket_id DESC
        """, (user_phone,))
    my_tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "home.html",
        genres=genres,
        movies=movies,
        my_tickets=my_tickets,
        search_ticket=search_ticket
    )


# =====================================================================
# 3. LUỒNG KHÁCH HÀNG - TRANG 2: CHỌN LỊCH CHIẾU, GHẾ 3D & ĐẶT VÉ (/booking/<movie_id>)
# =====================================================================
@app.route("/booking/<int:movie_id>", methods=["GET"])
def booking_page(movie_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    selected_showtime_id = request.args.get("showtime_id", type=int)
    selected_date = request.args.get("show_date", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
    current_movie = cursor.fetchone()
    if not current_movie:
        cursor.close()
        conn.close()
        return redirect(url_for("customer_home"))

    cursor.execute("""
        SELECT * FROM showtimes
        WHERE movie_id = %s
        ORDER BY show_date ASC, show_time ASC
    """, (movie_id,))
    movie_showtimes = cursor.fetchall()

    if not movie_showtimes:
        cursor.execute("""
            INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price)
            VALUES (%s, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', '2026-11-04', '18:00', 50000)
        """, (movie_id,))
        conn.commit()
        cursor.execute("SELECT * FROM showtimes WHERE movie_id = %s ORDER BY show_date ASC, show_time ASC", (movie_id,))
        movie_showtimes = cursor.fetchall()

    available_dates = []
    for st in movie_showtimes:
        d_str = str(st["show_date"])
        if d_str not in available_dates:
            available_dates.append(d_str)

    current_showtime = None
    if selected_showtime_id:
        current_showtime = next((st for st in movie_showtimes if st["showtime_id"] == selected_showtime_id), None)

    if not current_showtime:
        if selected_date and selected_date in available_dates:
            current_showtime = next((st for st in movie_showtimes if str(st["show_date"]) == selected_date), movie_showtimes[0])
        else:
            current_showtime = movie_showtimes[0]

    active_date = str(current_showtime["show_date"])
    showtimes_for_date = [st for st in movie_showtimes if str(st["show_date"]) == active_date]

    cursor.execute("SELECT * FROM combos ORDER BY combo_price ASC")
    combos = cursor.fetchall()

    cursor.execute("SELECT seat_code FROM booked_seats WHERE showtime_id = %s", (current_showtime["showtime_id"],))
    occupied_seats = [row["seat_code"] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        "booking.html",
        current_movie=current_movie,
        available_dates=available_dates,
        active_date=active_date,
        showtimes_for_date=showtimes_for_date,
        current_showtime=current_showtime,
        combos=combos,
        occupied_seats=occupied_seats
    )


@app.route("/api/pov")
def api_pov():
    seat = request.args.get("seat", "D6")
    base_price = float(request.args.get("base_price", 50000))
    return jsonify(calculate_seat_3d_pov(seat, base_price))


# =====================================================================
# 4. GIAO DIỆN QUẢN TRỊ VIÊN ĐỘC LẬP CÓ MENU SIDEBAR 3 GẠCH (/admin)
# =====================================================================
@app.route("/admin", methods=["GET"])
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        flash("Vui lòng đăng nhập bằng tài khoản Quản trị viên / Nhân viên!", "error")
        return redirect(url_for("login"))

    active_tab = request.args.get("tab", "overview").strip()
    search_query = request.args.get("q", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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

    cursor.close()
    conn.close()

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


# =====================================================================
# 5. CÁC ROUTE XỬ LÝ DỮ LIỆU CRUD CHO ADMIN & ĐẶT VÉ
# =====================================================================
@app.route("/add_ticket", methods=["POST"])
def add_ticket():
    ticket_code = request.form.get("ticket_code", "").strip().upper()
    movie_id = int(request.form.get("movie_id", 1))
    showtime_id = int(request.form.get("showtime_id", 1))
    customer_name = request.form.get("customer_name", "Khách hàng Beta").strip()
    customer_phone = request.form.get("customer_phone", "0988123456").strip()
    cinema_name = request.form.get("cinema_name", "Beta Thanh Xuân").strip()
    seats_raw = request.form.get("seats_text", "").strip().upper()
    combo_id = int(request.form.get("combo_id", 1) or 1)
    payment_method = request.form.get("payment_method", "Chuyển khoản QR").strip()
    from_admin = request.form.get("from_admin", "0") == "1"

    seat_list = [s.strip() for s in seats_raw.split(",") if s.strip()]
    if not ticket_code or not seat_list:
        flash("Vui lòng chọn ít nhất 1 ghế trên sơ đồ và nhập mã vé!", "error")
        if from_admin:
            return redirect(url_for("admin_dashboard", tab="tickets"))
        return redirect(url_for("booking_page", movie_id=movie_id, showtime_id=showtime_id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT base_price, cinema_name, movie_id FROM showtimes WHERE showtime_id = %s", (showtime_id,))
    st_row = cursor.fetchone()
    base_price = float(st_row["base_price"]) if st_row else 50000.0
    if st_row:
        cinema_name = st_row["cinema_name"]
        movie_id = st_row["movie_id"]

    cursor.execute("SELECT combo_name, combo_price FROM combos WHERE combo_id = %s", (combo_id,))
    cb_row = cursor.fetchone()
    combo_name = cb_row["combo_name"] if cb_row else "Không dùng Combo"
    combo_price = float(cb_row["combo_price"]) if cb_row else 0.0

    total_seat_money = 0.0
    for s in seat_list:
        r_char = s[0] if s else "D"
        if r_char in ["A", "B", "C"]:
            total_seat_money += base_price
        elif r_char in ["D", "E", "F"]:
            total_seat_money += (base_price + 15000)
        else:
            total_seat_money += (base_price + 20000)
    unit_price = round(total_seat_money / len(seat_list), 2)

    try:
        cursor.execute("""
            INSERT INTO tickets (ticket_code, movie_id, showtime_id, customer_name, customer_phone, cinema_name, seats_text, seat_count, unit_price, combo_name, combo_price, payment_method, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Đã thanh toán')
        """, (
            ticket_code, movie_id, showtime_id, customer_name, customer_phone,
            cinema_name, ", ".join(seat_list), len(seat_list), unit_price,
            combo_name, combo_price, payment_method
        ))
        new_ticket_id = cursor.lastrowid

        for s in seat_list:
            cursor.execute(
                "INSERT INTO booked_seats (ticket_id, showtime_id, movie_id, seat_code) VALUES (%s, %s, %s, %s)",
                (new_ticket_id, showtime_id, movie_id, s)
            )

        conn.commit()
        flash(f"Đặt vé thành công! Mã vé: {ticket_code} | Ghế: {', '.join(seat_list)}", "success")
        if from_admin:
            return redirect(url_for("admin_dashboard", tab="tickets"))
        return redirect(url_for("customer_home", q=ticket_code) + "#myTicketsSection")

    except mysql.connector.IntegrityError:
        conn.rollback()
        flash("Lỗi trùng dữ liệu: Mã vé đã tồn tại hoặc ghế bạn chọn trong suất chiếu này vừa có người đặt!", "error")
        if from_admin:
            return redirect(url_for("admin_dashboard", tab="tickets"))
        return redirect(url_for("booking_page", movie_id=movie_id, showtime_id=showtime_id))
    finally:
        cursor.close()
        conn.close()


@app.route("/update_ticket/<int:ticket_id>", methods=["POST"])
def update_ticket(ticket_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    customer_name = request.form.get("customer_name", "").strip()
    customer_phone = request.form.get("customer_phone", "").strip()
    cinema_name = request.form.get("cinema_name", "").strip()
    seats_raw = request.form.get("seats_text", "").strip().upper()
    unit_price = float(request.form.get("unit_price", 65000) or 65000)
    combo_name = request.form.get("combo_name", "Không dùng Combo").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    payment_method = request.form.get("payment_method", "Chuyển khoản QR").strip()
    payment_status = request.form.get("payment_status", "Đã thanh toán").strip()

    seat_list = [s.strip() for s in seats_raw.split(",") if s.strip()]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT movie_id, showtime_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
    tk = cursor.fetchone()

    if tk and seat_list:
        try:
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
            conn.commit()
            flash("Đã cập nhật thông tin vé và sơ đồ ghế thành công!", "success")
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("Không thể đổi sang ghế đã có người khác đặt trong cùng suất chiếu!", "error")

    cursor.close()
    conn.close()
    return redirect(url_for("admin_dashboard", tab="tickets"))


@app.route("/delete_ticket/<int:ticket_id>", methods=["GET"])
def delete_ticket(ticket_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã hủy vé và giải phóng ghế trống trên sơ đồ suất chiếu.", "success")
    return redirect(url_for("admin_dashboard", tab="tickets"))


@app.route("/add_movie", methods=["POST"])
def add_movie():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO movies (title, director, actors, genre, age_rating, duration, rating_score, status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (title, director, actors, genre, age_rating, duration, rating_score, status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url))
    new_movie_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price) VALUES
        (%s, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', %s, '19:30', 50000),
        (%s, 'Beta Mỹ Đình', 'Phòng 02 • IMAX Laser 3D', %s, '21:15', 55000)
    """, (new_movie_id, release_date, new_movie_id, release_date))

    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã thêm phim '{title}' kèm 2 suất chiếu mặc định thành công!", "success")
    return redirect(url_for("admin_dashboard", tab="movies"))


@app.route("/update_movie/<int:movie_id>", methods=["POST"])
def update_movie(movie_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE movies
        SET title = %s, director = %s, actors = %s, genre = %s, age_rating = %s,
            duration = %s, rating_score = %s, status_tab = %s, is_hot = %s,
            release_date = %s, end_date = %s, description = %s,
            poster_url = %s, quote = %s, video_url = %s
        WHERE movie_id = %s
    """, (title, director, actors, genre, age_rating, duration, rating_score, status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url, movie_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã cập nhật thông tin phim '{title}'!", "success")
    return redirect(url_for("admin_dashboard", tab="movies"))


@app.route("/delete_movie/<int:movie_id>", methods=["GET"])
def delete_movie(movie_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    if cursor.fetchone()[0] <= 1:
        cursor.close()
        conn.close()
        flash("Hệ thống cần giữ lại ít nhất 1 bộ phim!", "error")
        return redirect(url_for("admin_dashboard", tab="movies"))

    cursor.execute("DELETE FROM movies WHERE movie_id = %s", (movie_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã xóa bộ phim khỏi hệ thống.", "success")
    return redirect(url_for("admin_dashboard", tab="movies"))


@app.route("/add_showtime", methods=["POST"])
def add_showtime():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    movie_id = int(request.form.get("movie_id", 1))
    cinema_name = request.form.get("cinema_name", "Beta Thanh Xuân").strip()
    hall_name = request.form.get("hall_name", "Phòng 01 • Dolby Atmos 2D").strip()
    show_date = request.form.get("show_date", "2026-11-05").strip()
    show_time = request.form.get("show_time", "20:00").strip()
    base_price = float(request.form.get("base_price", 50000) or 50000)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (movie_id, cinema_name, hall_name, show_date, show_time, base_price))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã thêm suất chiếu mới: Ngày {show_date} lúc {show_time}!", "success")
    return redirect(url_for("admin_dashboard", tab="showtimes"))


@app.route("/update_showtime/<int:showtime_id>", methods=["POST"])
def update_showtime(showtime_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    movie_id = int(request.form.get("movie_id", 1))
    cinema_name = request.form.get("cinema_name", "").strip()
    hall_name = request.form.get("hall_name", "").strip()
    show_date = request.form.get("show_date", "").strip()
    show_time = request.form.get("show_time", "").strip()
    base_price = float(request.form.get("base_price", 50000) or 50000)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE showtimes
        SET movie_id = %s, cinema_name = %s, hall_name = %s, show_date = %s, show_time = %s, base_price = %s
        WHERE showtime_id = %s
    """, (movie_id, cinema_name, hall_name, show_date, show_time, base_price, showtime_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã cập nhật suất chiếu #{showtime_id}!", "success")
    return redirect(url_for("admin_dashboard", tab="showtimes"))


@app.route("/delete_showtime/<int:showtime_id>", methods=["GET"])
def delete_showtime(showtime_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM showtimes WHERE showtime_id = %s", (showtime_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã xóa suất chiếu.", "success")
    return redirect(url_for("admin_dashboard", tab="showtimes"))


@app.route("/add_genre", methods=["POST"])
def add_genre():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    genre_name = request.form.get("genre_name", "").strip()
    if genre_name:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO genres (genre_name) VALUES (%s)", (genre_name,))
            conn.commit()
            flash(f"Đã thêm thể loại '{genre_name}'!", "success")
        except mysql.connector.IntegrityError:
            flash("Thể loại này đã tồn tại!", "error")
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/update_genre/<int:genre_id>", methods=["POST"])
def update_genre(genre_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    new_name = request.form.get("genre_name", "").strip()
    old_name = request.form.get("old_genre_name", "").strip()
    if new_name:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE genres SET genre_name = %s WHERE genre_id = %s", (new_name, genre_id))
            if old_name and old_name != new_name:
                cursor.execute("UPDATE movies SET genre = REPLACE(genre, %s, %s) WHERE genre LIKE %s", (old_name, new_name, f"%{old_name}%"))
            conn.commit()
            flash(f"Đã đổi thể loại '{old_name}' thành '{new_name}'!", "success")
        except mysql.connector.IntegrityError:
            flash("Tên thể loại bị trùng!", "error")
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/delete_genre/<int:genre_id>", methods=["GET"])
def delete_genre(genre_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM genres WHERE genre_id = %s", (genre_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã xóa thể loại phim.", "success")
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/add_combo", methods=["POST"])
def add_combo():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    combo_name = request.form.get("combo_name", "").strip()
    combo_desc = request.form.get("combo_desc", "").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    if combo_name:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO combos (combo_name, combo_desc, combo_price) VALUES (%s, %s, %s)", (combo_name, combo_desc, combo_price))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Đã thêm gói '{combo_name}'!", "success")
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/update_combo/<int:combo_id>", methods=["POST"])
def update_combo(combo_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    combo_name = request.form.get("combo_name", "").strip()
    combo_desc = request.form.get("combo_desc", "").strip()
    combo_price = float(request.form.get("combo_price", 0) or 0)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE combos SET combo_name = %s, combo_desc = %s, combo_price = %s WHERE combo_id = %s", (combo_name, combo_desc, combo_price, combo_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Đã cập nhật gói '{combo_name}'!", "success")
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/delete_combo/<int:combo_id>", methods=["GET"])
def delete_combo(combo_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM combos WHERE combo_id = %s", (combo_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã xóa gói Combo.", "success")
    return redirect(url_for("admin_dashboard", tab="settings"))


@app.route("/add_user", methods=["POST"])
def add_user():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "123456").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    role = request.form.get("role", "customer").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, full_name, phone, role) VALUES (%s, %s, %s, %s, %s)",
            (username, password, full_name, phone, role)
        )
        conn.commit()
        flash(f"Đã tạo tài khoản '{username}' ({role}) thành công!", "success")
    except mysql.connector.IntegrityError:
        flash("Tên đăng nhập đã tồn tại!", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("admin_dashboard", tab="users"))


@app.route("/delete_user/<int:user_id>", methods=["GET"])
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    if user_id == session.get("user_id"):
        flash("Không thể tự xóa tài khoản đang đăng nhập!", "error")
        return redirect(url_for("admin_dashboard", tab="users"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Đã xóa tài khoản người dùng.", "success")
    return redirect(url_for("admin_dashboard", tab="users"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

@app.route('/admin/add-movie', methods=['POST'])
def add_movie():
    # Kiểm tra bảo mật quyền admin nếu cần
    if session.get('role') != 'admin':
        return "Bạn không có quyền thực hiện thao tác này!", 403
        
    title = request.form.get('title')
    image_url = request.form.get('image_url')
    trailer_url = request.form.get('trailer_url')
    
    # Kết nối cơ sở dữ liệu TiDB và lưu vào bảng movies
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO movies (title, image_url, trailer_url) VALUES (%s, %s, %s)",
        (title, image_url, trailer_url)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    # Thêm xong chuyển hướng về lại trang admin hoặc trang chủ
    return redirect('/home')
