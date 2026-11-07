import mysql.connector
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from utils.db_helper import db_cursor
from utils.helper import (
    login_required,
    is_valid_phone,
    parse_and_validate_seats,
    get_seat_type_and_price,
    calculate_seat_3d_pov
)

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/home", methods=["GET"])
@login_required
def customer_home():
    search_ticket = request.args.get("q", "").strip()
    user_phone = session.get("phone", "")

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT * FROM genres ORDER BY genre_id ASC")
        genres = cursor.fetchall()

        cursor.execute("SELECT * FROM movies ORDER BY movie_id ASC")
        movies = cursor.fetchall()

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

    return render_template(
        "home.html",
        genres=genres,
        movies=movies,
        my_tickets=my_tickets,
        search_ticket=search_ticket
    )


@customer_bp.route("/booking/<int:movie_id>", methods=["GET"])
@login_required
def booking_page(movie_id):
    selected_showtime_id = request.args.get("showtime_id", type=int)
    selected_date = request.args.get("show_date", "").strip()

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
        current_movie = cursor.fetchone()
        if not current_movie:
            flash("Không tìm thấy bộ phim yêu cầu!", "error")
            return redirect(url_for("customer.customer_home"))

        cursor.execute("""
            SELECT * FROM showtimes
            WHERE movie_id = %s
            ORDER BY show_date ASC, show_time ASC
        """, (movie_id,))
        movie_showtimes = cursor.fetchall()

        if not movie_showtimes:
            flash(f"Bộ phim '{current_movie['title']}' hiện chưa có suất chiếu nào được mở!", "error")
            return redirect(url_for("customer.customer_home"))

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


@customer_bp.route("/api/pov", methods=["GET"])
def api_pov():
    seat = request.args.get("seat", "D6")
    base_price = float(request.args.get("base_price", 50000))
    return jsonify(calculate_seat_3d_pov(seat, base_price))


@customer_bp.route("/add_ticket", methods=["POST"])
@login_required
def add_ticket():
    ticket_code = request.form.get("ticket_code", "").strip().upper()
    movie_id = int(request.form.get("movie_id", 1) or 1)
    showtime_id = int(request.form.get("showtime_id", 1) or 1)
    customer_name = request.form.get("customer_name", "Khách hàng Beta").strip()
    customer_phone = request.form.get("customer_phone", "").strip()
    cinema_name = request.form.get("cinema_name", "Beta Thanh Xuân").strip()
    seats_raw = request.form.get("seats_text", "")
    combo_id = int(request.form.get("combo_id", 1) or 1)
    payment_method = request.form.get("payment_method", "Chuyển khoản QR").strip()
    from_admin = request.form.get("from_admin", "0") == "1"

    seat_list = parse_and_validate_seats(seats_raw)
    if not ticket_code or not seat_list:
        flash("Vui lòng chọn ít nhất 1 mã ghế hợp lệ (A1-H12) và nhập mã vé!", "error")
        if from_admin:
            return redirect(url_for("admin.admin_dashboard", tab="tickets"))
        return redirect(url_for("customer.booking_page", movie_id=movie_id, showtime_id=showtime_id))

    if not is_valid_phone(customer_phone):
        flash("Số điện thoại nhận vé không hợp lệ!", "error")
        if from_admin:
            return redirect(url_for("admin.admin_dashboard", tab="tickets"))
        return redirect(url_for("customer.booking_page", movie_id=movie_id, showtime_id=showtime_id))

    try:
        with db_cursor(dictionary=True, commit=True) as (_, cursor):
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

            total_seat_money = sum(get_seat_type_and_price(s, base_price)[1] for s in seat_list)
            unit_price = round(total_seat_money / len(seat_list), 2)

            cursor.execute("""
                INSERT INTO tickets (
                    ticket_code, movie_id, showtime_id, customer_name, customer_phone,
                    cinema_name, seats_text, seat_count, unit_price,
                    combo_name, combo_price, payment_method, payment_status
                )
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

        flash(f"Đặt vé thành công! Mã vé: {ticket_code} | Ghế: {', '.join(seat_list)}", "success")
        if from_admin:
            return redirect(url_for("admin.admin_dashboard", tab="tickets"))
        return redirect(url_for("customer.customer_home", q=ticket_code) + "#myTicketsSection")

    except mysql.connector.IntegrityError:
        flash("Lỗi trùng dữ liệu: Mã vé đã tồn tại hoặc ghế bạn chọn vừa có người khác đặt trước!", "error")
        if from_admin:
            return redirect(url_for("admin.admin_dashboard", tab="tickets"))
        return redirect(url_for("customer.booking_page", movie_id=movie_id, showtime_id=showtime_id))
