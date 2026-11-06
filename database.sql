CREATE DATABASE IF NOT EXISTS beta_cinema_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE beta_cinema_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS booked_seats;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS showtimes;
DROP TABLE IF EXISTS combos;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. BẢNG TÀI KHOẢN NGƯỜI DÙNG (PHÂN QUYỀN ĐĂNG NHẬP)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer', -- 'admin' hoặc 'customer'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. BẢNG THỂ LOẠI PHIM
CREATE TABLE genres (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. BẢNG PHIM
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

-- 4. BẢNG LỊCH CHIẾU (CHỌN NGÀY, CHỌN GIỜ, RẠP & PHÒNG)
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

-- 5. BẢNG COMBO BẮP NƯỚC
CREATE TABLE combos (
    combo_id INT AUTO_INCREMENT PRIMARY KEY,
    combo_name VARCHAR(150) NOT NULL,
    combo_desc VARCHAR(255) NOT NULL,
    combo_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. BẢNG VÉ ĐẶT
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

-- 7. BẢNG GHẾ ĐÃ ĐẶT THEO SUẤT CHIẾU
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