import math
import re
from functools import wraps
from flask import session, redirect, url_for, flash

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]
COLS = list(range(1, 13))
PHONE_REGEX = re.compile(r"^0\d{8,10}$")


def login_required(f):
    """Decorator kiểm tra người dùng đã đăng nhập hay chưa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator kiểm tra quyền Quản trị viên (RBAC)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Vui lòng đăng nhập bằng tài khoản Quản trị viên / Nhân viên!", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def is_valid_phone(phone: str) -> bool:
    """Kiểm tra định dạng số điện thoại hợp lệ (bắt đầu bằng số 0, từ 9-11 chữ số)."""
    return bool(PHONE_REGEX.match(phone.strip()))


def parse_and_validate_seats(seats_raw: str) -> list[str]:
    """Chuẩn hóa và kiểm tra danh sách mã ghế hợp lệ (A1 -> H12), loại bỏ ghế trùng."""
    valid_seats = []
    for item in seats_raw.upper().split(","):
        code = item.strip()
        if len(code) >= 2 and code[0] in ROWS:
            try:
                col_num = int(code[1:])
                if col_num in COLS and code not in valid_seats:
                    valid_seats.append(code)
            except ValueError:
                continue
    return valid_seats


def get_seat_type_and_price(seat_code: str, base_price: float = 50000.0) -> tuple[str, int]:
    """Tính hạng ghế và giá tiền dựa trên ký tự hàng ghế (Quy tắc BR01)."""
    row_char = seat_code[0].upper() if seat_code else "D"
    if row_char in ["A", "B", "C"]:
        return "Ghế Thường", int(base_price)
    if row_char in ["D", "E", "F"]:
        return "Ghế VIP", int(base_price + 15000)
    return "Ghế Đôi Sweetbox", int(base_price + 20000)


def calculate_seat_3d_pov(seat_code: str, base_price: float = 50000.0) -> dict:
    """Thuật toán tính tọa độ hình học không gian 3D POV và điểm trải nghiệm từ vị trí ghế."""
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

    seat_type, price = get_seat_type_and_price(f"{row_char}{col_num}", base_price)

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
