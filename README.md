# BETA CINE+ - Website đặt vé xem phim trực tuyến

## 1. Công nghệ sử dụng

- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- Database: MySQL / TiDB Cloud
- Deployment: Render
- Quản lý mã nguồn: GitHub

## 2. Yêu cầu môi trường

- Git
- Python 3.13
- MySQL Server

## 3. Hướng dẫn chạy dự án trên Windows (PowerShell)

### Bước 1: Clone repository

```powershell
git clone https://github.com/hoangD-maker/Web-xem-film.git
cd Web-xem-film
```

### Bước 2: Tạo và kích hoạt môi trường ảo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn chạy script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Sau đó kích hoạt lại môi trường ảo.

### Bước 3: Cài đặt thư viện

```powershell
python -m pip install -r requirements.txt
```

### Bước 4: Khởi tạo database local

Đăng nhập MySQL:

```powershell
mysql -h 127.0.0.1 -u root -p
```

Tạo database:

```sql
CREATE DATABASE IF NOT EXISTS beta_cinema_db;
exit;
```

### Bước 5: Cấu hình kết nối database

```powershell
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
$env:DB_USER = "root"
$env:DB_PASSWORD = Read-Host "Nhap mat khau MySQL"
$env:DB_NAME = "beta_cinema_db"
```

### Bước 6: Khởi tạo dữ liệu mẫu

```powershell
python fix_db.py
```

**Cảnh báo:** Chỉ chạy fix_db.py trên database thử nghiệm
local. File này xóa và tạo lại các bảng, làm mất dữ liệu cũ.

### Bước 7: Chạy website

```powershell
python app.py
```

Truy cập: http://127.0.0.1:5000

## 4. Tài khoản thử nghiệm local

| Vai trò | Username | Password |
|---|---|---|
| Khách hàng | khachhang | 123456 |
| Quản trị viên | admin | 123456 |

## 5. Quy trình đóng góp mã nguồn

Cập nhật code mới nhất và tạo nhánh riêng:

```bash
git switch main
git pull origin main
git switch -c ten-thanh-vien/ten-chuc-nang
```

Sau khi hoàn thành và kiểm thử:

```bash
git add ten-file
git commit -m "Mo ta thay doi"
git push -u origin ten-thanh-vien/ten-chuc-nang
```

Tạo Pull Request trên GitHub và chờ review trước khi merge.

## 6. Lưu ý

- Không chỉnh sửa trực tiếp trên nhánh main.
- Không commit mật khẩu database, file .env hoặc .venv.
- Sử dụng database local để kiểm thử.
- Không chạy lại fix_db.py nếu muốn giữ dữ liệu hiện tại.
- Khi chạy lại dự án, chỉ cần kích hoạt môi trường ảo,
  cấu hình biến môi trường và chạy python app.py.