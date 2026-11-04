# LENLEARN Admin

Web quản trị tiếng Việt, kết nối API FastAPI hiện có. Dùng HTML/CSS/JavaScript và Node.js, không cần cài thư viện hay build.

## Chạy local

Yêu cầu Node.js 20+ và backend đã cấu hình database/migration theo README của dự án.

Terminal backend (từ thư mục gốc):

```powershell
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Nếu chưa có tài khoản ADMIN, tạo tài khoản riêng bằng công cụ backend sau khi chạy migration:

```powershell
cd backend
python create_admin.py --username admin --email admin@example.com --full-name "Administrator"
```

Công cụ hỏi mật khẩu trong terminal. Không có mật khẩu mặc định; đăng ký công khai không cấp quyền ADMIN.

Terminal web (từ thư mục gốc):

```powershell
cd web_admin
npm start
```

Mở **http://127.0.0.1:3001** và đăng nhập bằng tài khoản ADMIN.

Đổi backend hoặc cổng bằng biến môi trường PowerShell trước khi chạy:

```powershell
$env:BACKEND_URL = 'http://127.0.0.1:8000'
$env:PORT = '3001'
npm start
```

Máy chủ bind `127.0.0.1` theo mặc định. Đặt `HOST` để truy cập qua mạng nội bộ; khi đưa lên Internet cần reverse proxy HTTPS. Chạy bằng máy chủ Node, không mở index.html trực tiếp hoặc qua Live Server: proxy `/api` giúp không cần sửa CORS backend. BACKEND_URL là cấu hình máy chủ. File .env không tự nạp; dùng biến môi trường như trên.

## Chức năng và API

| Màn hình | Chức năng | Backend |
| --- | --- | --- |
| Đăng nhập | Đăng nhập, kiểm tra ADMIN từ hồ sơ | POST /auth/login, GET /users/me |
| Tổng quan | Người dùng, quản trị viên, từ vựng, chủ đề, lượt kiểm tra hoàn thành; phân bố từ theo chủ đề | GET /admin/summary, GET /admin/topics |
| Từ vựng | Tìm từ/nghĩa, lọc chủ đề, phân trang, chi tiết, thêm/sửa nghĩa và ví dụ chính, gán nhiều chủ đề | GET/POST /admin/vocabularies, PUT /admin/vocabularies/{id} |
| Chủ đề | Tìm kiếm, phân trang, thêm/sửa, xác nhận xóa chủ đề rỗng | GET/POST /admin/topics, PUT/DELETE /admin/topics/{id} |
| Người dùng | Xem, tìm kiếm và lọc vai trò trong nhóm đang tải | GET /admin/users?offset=...&limit=100 |

Người dùng tải theo nhóm 99 bản ghi, lấy thêm 1 để xác định nhóm tiếp theo. Tìm kiếm/lọc chỉ áp dụng nhóm hiện tại và được ghi rõ trên giao diện. Các dữ liệu khác phân trang và lọc trên trình duyệt do API trả toàn bộ danh sách.

Token giữ trong sessionStorage của tab, xóa khi đăng xuất hoặc backend trả 401/403. Backend kiểm tra quyền trên mọi API quản trị. Không lưu mật khẩu. Dữ liệu được escape khi hiển thị. Không có dữ liệu mẫu hoặc thao tác ghi khi mở trang; dữ liệu thay đổi khi lưu biểu mẫu hoặc xác nhận xóa.

Backend chưa có xóa từ vựng, khóa/xóa người dùng, đổi vai trò, hay CRUD tài sản ảnh/âm thanh. Giao diện quản lý tài nguyên học tập trong phạm vi API hiện có. Sửa từ giữ nguyên nghĩa/ví dụ bổ sung; ví dụ chính đã có không thể xóa trắng theo ràng buộc backend.

## Kiểm tra

```powershell
npm run check
npm test
```

Test proxy thật với backend giả lập: chuyển tiếp bearer token và payload, giữ mã lỗi, chặn route ngoài phạm vi/truy cập file và xử lý backend lỗi. Kiểm tra tích hợp thực cần backend/database: đăng nhập ADMIN, tạo chủ đề, tạo từ trong chủ đề, sửa từ, gỡ liên kết và xóa chủ đề rỗng. Tài khoản USER phải bị từ chối.

Kiểm tra giao diện tự động với backend giả lập (Node.js 22+, Chrome trên Windows):

```powershell
npm run test:browser
```

Mặc định dùng `C:/Program Files/Google/Chrome/Application/chrome.exe`. Đổi đường dẫn trình duyệt bằng biến `ADMIN_TEST_BROWSER` nếu dùng Edge hoặc cài Chrome ở nơi khác. Bài kiểm tra mở trình duyệt headless, kiểm tra từ chối USER, đăng nhập ADMIN, thêm/xóa chủ đề rỗng, thêm/sửa/xem từ, tìm tiếng Việt không dấu, lọc người dùng, menu mobile và đăng xuất. Hai ảnh desktop/mobile lưu trong thư mục tạm của hệ điều hành. Bài kiểm tra không dùng tài khoản hoặc database thật.
