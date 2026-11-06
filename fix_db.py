import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "beta_cinema_db"),
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci"
)
cursor = conn.cursor()

cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
for tbl in ["booked_seats", "tickets", "showtimes", "combos", "movies", "genres", "users"]:
    cursor.execute(f"DROP TABLE IF EXISTS {tbl};")
cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

cursor.execute("""
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE genres (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE movies (
    movie_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    director VARCHAR(100) NOT NULL,
    actors VARCHAR(255) NOT NULL DEFAULT 'Đang cập nhật',
    genre VARCHAR(150) NOT NULL,
    age_rating VARCHAR(10) NOT NULL DEFAULT 'T16',
    duration VARCHAR(50) NOT NULL,
    rating_score DECIMAL(3, 1) NOT NULL DEFAULT 9.0,
    status_tab VARCHAR(30) NOT NULL DEFAULT 'showing',
    is_hot TINYINT(1) NOT NULL DEFAULT 1,
    release_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT NOT NULL,
    poster_url VARCHAR(500) NOT NULL,
    quote VARCHAR(255) NOT NULL,
    video_url VARCHAR(500) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE showtimes (
    showtime_id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    cinema_name VARCHAR(100) NOT NULL,
    hall_name VARCHAR(100) NOT NULL,
    show_date DATE NOT NULL,
    show_time VARCHAR(20) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL DEFAULT 50000.00,
    CONSTRAINT fk_showtime_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE combos (
    combo_id INT AUTO_INCREMENT PRIMARY KEY,
    combo_name VARCHAR(150) NOT NULL,
    combo_desc VARCHAR(255) NOT NULL,
    combo_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_code VARCHAR(30) NOT NULL UNIQUE,
    movie_id INT NOT NULL,
    showtime_id INT NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(30) NOT NULL DEFAULT '0988123456',
    cinema_name VARCHAR(100) NOT NULL,
    seats_text VARCHAR(255) NOT NULL,
    seat_count INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 65000.00,
    combo_name VARCHAR(150) NOT NULL DEFAULT 'Không dùng Combo',
    combo_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'Chuyển khoản QR',
    payment_status VARCHAR(40) NOT NULL DEFAULT 'Đã thanh toán',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ticket_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_showtime FOREIGN KEY (showtime_id) REFERENCES showtimes(showtime_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

cursor.execute("""
CREATE TABLE booked_seats (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    showtime_id INT NOT NULL,
    movie_id INT NOT NULL,
    seat_code VARCHAR(10) NOT NULL,
    UNIQUE KEY uq_showtime_seat (showtime_id, seat_code),
    CONSTRAINT fk_seat_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    CONSTRAINT fk_seat_showtime FOREIGN KEY (showtime_id) REFERENCES showtimes(showtime_id) ON DELETE CASCADE,
    CONSTRAINT fk_seat_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")

# 1. Nạp Tài khoản mẫu (Admin & Khách hàng)
cursor.execute("""
INSERT INTO users (username, password, full_name, phone, role) VALUES
('admin', '123456', 'Quản Trị Viên Beta', '0901234567', 'admin'),
('nhanvien', '123456', 'Nhân Viên Quầy Vé', '0909888777', 'admin'),
('khachhang', '123456', 'Nguyễn Văn An', '0912345678', 'customer'),
('khachvip', '123456', 'Trần Thị Bình', '0987654321', 'customer');
""")

# 2. Nạp Thể loại
cursor.execute("""
INSERT INTO genres (genre_name) VALUES
('Tâm lý'), ('Tình cảm'), ('Trinh thám'), ('Hài hước'),
('Hành động'), ('Kinh dị'), ('Khoa học viễn tưởng'), ('Gia đình');
""")

# 3. Nạp Combo
cursor.execute("""
INSERT INTO combos (combo_name, combo_desc, combo_price) VALUES
('Không dùng Combo', 'Chỉ đặt vé xem phim tiêu chuẩn', 0),
('Beta Sweet Combo', '1 Bắp rang bơ lớn + 1 Nước ngọt có gas cỡ lớn', 69000),
('Couple Cinema Combo', '1 Bắp lớn 2 vị Phô mai & Caramel + 2 Nước lớn', 119000),
('Family VIP Party Pack', '2 Bắp lớn + 4 Nước ngọt + 2 Snack khoai tây', 199000);
""")

# 4. Nạp Phim
cursor.execute("""
INSERT INTO movies (title, director, actors, genre, age_rating, duration, rating_score, status_tab, is_hot, release_date, end_date, description, poster_url, quote, video_url) VALUES
(
    'Chị Chị Em Em 3', 'Vũ Ngọc Đãng', 'Minh Hằng, Ngọc Trinh, Thuận Nguyễn', 'Tâm lý, Tình cảm', 'T18', '122 phút', 9.1, 'showing', 1,
    '2026-10-30', '2026-12-30',
    'Cuộc đối đầu đầy kịch tính và những bí mật hào môn sâu kín giữa những người phụ nữ quyền lực, nơi tình thân và tham vọng bị đặt lên bàn cân sinh tử.',
    'https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=600&q=80',
    'Đằng sau hào quang là những bí mật không thể chôn vùi!',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4'
),
(
    'Án Mạng Karaoke', 'Trần Hữu Tấn', 'Mạc Văn Khoa, Lê Lộc, Quốc Cường', 'Trinh thám, Hài hước', 'T16', '96 phút', 8.7, 'showing', 1,
    '2026-10-30', '2026-12-20',
    'Một vụ án bí ẩn bất ngờ xảy ra ngay trong phòng hát karaoke lúc nửa đêm, kéo cả nhóm bạn vào màn suy luận vừa gay cấn vừa dở khóc dở cười.',
    'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=600&q=80',
    'Ai là hung thủ thực sự sau tiếng nhạc xập xình?',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4'
),
(
    'Trại Buôn Người', 'Lê Văn Kiệt', 'Quách Ngọc Ngoan, Thanh Hoa', 'Hành động, Tâm lý', 'T18', '135 phút', 9.3, 'showing', 0,
    '2026-10-25', '2026-12-25',
    'Hành trình giải cứu nghẹt thở và cuộc đấu tranh sinh tồn của những nạn nhân bị giam giữ tại sào huyệt tội phạm xuyên biên giới.',
    'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80',
    'Không một ai bị bỏ lại phía sau trong cuộc đào thoát sinh tử!',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4'
),
(
    'Quỷ Ăn Tạng 4: Hồ Tinh', 'Taweewat Wantha', 'Nadech Kugimiya, Denise Jelilcha', 'Kinh dị, Hành động', 'T18', '111 phút', 8.9, 'showing', 0,
    '2026-10-09', '2026-12-15',
    'Gia đình Yak tiếp tục đối mặt với thế lực tà thuật cổ xưa trỗi dậy từ vùng hồ sâu rừng rậm, nơi những âm hồn khát máu rình rập trong đêm tối.',
    'https://images.unsplash.com/photo-1509248961158-e54f6934749c?auto=format&fit=crop&w=600&q=80',
    'Khi màn đêm buông xuống, tuyệt đối đừng nghe tiếng gọi bên hồ!',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4'
),
(
    'Dune: Hành Tinh Cát - Phần Hai', 'Denis Villeneuve', 'Timothée Chalamet, Zendaya, Rebecca Ferguson', 'Khoa học viễn tưởng, Hành động', 'T16', '166 phút', 9.6, 'special', 1,
    '2026-10-01', '2026-12-31',
    'Paul Atreides hợp nhất với tộc người Fremen để thực hiện cuộc trả thù những kẻ đã hủy hoại gia tộc mình và định đoạt vận mệnh toàn vũ trụ.',
    'https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80',
    'Kẻ nào làm chủ được Hương Dược, kẻ đó làm chủ vũ trụ!',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4'
),
(
    'Lật Mặt 8: Vòng Tay Nắng', 'Lý Hải', 'Quốc Cường, Trung Dũng, Kiều Trinh', 'Gia đình, Tâm lý', 'K', '138 phút', 9.4, 'upcoming', 1,
    '2026-11-20', '2027-01-15',
    'Câu chuyện ấm áp về tình cảm gia đình Việt Nam vượt qua những thử thách của cuộc sống đời thường nơi miền quê đầy nắng gió.',
    'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=600&q=80',
    'Gia đình luôn là bến đỗ bình yên nhất sau mọi giông bão.',
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4'
);
""")

# 5. Nạp Lịch chiếu
cursor.execute("""
INSERT INTO showtimes (movie_id, cinema_name, hall_name, show_date, show_time, base_price) VALUES
(1, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', '2026-11-04', '18:00', 50000),
(1, 'Beta Thanh Xuân', 'Phòng 02 • IMAX Laser 2D', '2026-11-04', '20:15', 55000),
(1, 'Beta Mỹ Đình', 'Phòng 03 • Digital 2D', '2026-11-04', '22:00', 50000),
(1, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', '2026-11-05', '19:00', 50000),
(1, 'Beta Giải Phóng', 'Phòng 04 • VIP Gold Class', '2026-11-05', '21:15', 60000),
(1, 'Beta Thái Nguyên', 'Phòng 01 • Dolby Atmos 2D', '2026-11-06', '20:00', 45000),
(2, 'Beta Thanh Xuân', 'Phòng 03 • Digital 2D', '2026-11-04', '17:45', 45000),
(2, 'Beta Mỹ Đình', 'Phòng 02 • Dolby Atmos 2D', '2026-11-04', '19:30', 50000),
(2, 'Beta Thanh Xuân', 'Phòng 03 • Digital 2D', '2026-11-05', '20:30', 50000),
(2, 'Beta Thái Nguyên', 'Phòng 02 • Digital 2D', '2026-11-06', '18:30', 45000),
(3, 'Beta Mỹ Đình', 'Phòng 01 • IMAX Laser 2D', '2026-11-04', '19:00', 55000),
(3, 'Beta Thanh Xuân', 'Phòng 02 • Dolby Atmos 2D', '2026-11-04', '21:30', 50000),
(3, 'Beta Giải Phóng', 'Phòng 01 • Digital 2D', '2026-11-05', '20:00', 50000),
(4, 'Beta Thanh Xuân', 'Phòng 04 • Dolby Atmos 2D', '2026-11-04', '20:45', 50000),
(4, 'Beta Mỹ Đình', 'Phòng 02 • IMAX Laser 2D', '2026-11-04', '22:30', 55000),
(4, 'Beta Thái Nguyên', 'Phòng 01 • Digital 2D', '2026-11-05', '21:45', 45000),
(5, 'Beta Thanh Xuân', 'Phòng 01 • IMAX Laser 3D', '2026-11-04', '19:45', 60000),
(5, 'Beta Mỹ Đình', 'Phòng 01 • IMAX Laser 3D', '2026-11-05', '20:15', 60000),
(5, 'Beta Giải Phóng', 'Phòng 02 • Dolby Atmos 3D', '2026-11-06', '21:00', 55000),
(6, 'Beta Thanh Xuân', 'Phòng 01 • Dolby Atmos 2D', '2026-11-20', '18:30', 50000),
(6, 'Beta Mỹ Đình', 'Phòng 02 • Digital 2D', '2026-11-20', '20:30', 50000),
(6, 'Beta Thái Nguyên', 'Phòng 01 • Dolby Atmos 2D', '2026-11-21', '19:30', 45000);
""")

# 6. Nạp Vé mẫu
cursor.execute("""
INSERT INTO tickets (ticket_code, movie_id, showtime_id, customer_name, customer_phone, cinema_name, seats_text, seat_count, unit_price, combo_name, combo_price, payment_method, payment_status) VALUES
('VE001', 1, 1, 'Nguyễn Văn An', '0912345678', 'Beta Thanh Xuân', 'C5, C6', 2, 50000.00, 'Beta Sweet Combo', 69000.00, 'Chuyển khoản QR', 'Đã thanh toán'),
('VE002', 1, 1, 'Trần Thị Bình', '0987654321', 'Beta Thanh Xuân', 'E7, E8', 2, 65000.00, 'Couple Cinema Combo', 119000.00, 'Ví MoMo', 'Đã thanh toán'),
('VE003', 1, 1, 'Lê Hoàng Nam', '0909112233', 'Beta Thanh Xuân', 'F5', 1, 65000.00, 'Không dùng Combo', 0.00, 'VNPay QR', 'Đã thanh toán');
""")

cursor.execute("""
INSERT INTO booked_seats (ticket_id, showtime_id, movie_id, seat_code) VALUES
(1, 1, 1, 'C5'), (1, 1, 1, 'C6'),
(2, 1, 1, 'E7'), (2, 1, 1, 'E8'),
(3, 1, 1, 'F5');
""")

conn.commit()
print("✅ Đã tạo 7 bảng CSDL (Users, Genres, Movies, Showtimes, Combos, Tickets, Booked_Seats) thành công!")
cursor.close()
conn.close()