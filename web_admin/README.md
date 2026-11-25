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
| Từ vựng | Tìm từ/nghĩa, lọc chủ đề, phân trang, thêm/sửa/xóa từng nghĩa và ví dụ, gán nhiều chủ đề | GET/POST /admin/vocabularies, PUT /admin/vocabularies/{id} |
| Chủ đề | Tìm kiếm, phân trang, thêm/sửa, xác nhận xóa chủ đề rỗng | GET/POST /admin/topics, PUT/DELETE /admin/topics/{id} |
| Người dùng | Xem, tìm kiếm, lọc vai trò; xem tiến độ; khóa/mở khóa và xóa tài khoản người học | GET /admin/users, GET /admin/users/{id}, PATCH /admin/users/{id}/lock, DELETE /admin/users/{id} |
| Quản lý quiz | Lọc lượt làm bài, xem câu hỏi và câu trả lời, thống kê theo loại bài và loại câu | GET /admin/quizzes, GET /admin/quizzes/summary, GET /admin/quizzes/{id} |
| Thống kê học tập | Người học hoạt động, lượt học, tỷ lệ đúng, từ khó và tỷ lệ quay lại | GET /admin/analytics/learning |
| Thống kê trò chơi | Số lượt bắt đầu, điểm trung bình, màn vượt qua và từ hay bỏ lỡ theo trò chơi | GET /admin/analytics/games |

Thống kê dùng ngày theo giờ Việt Nam. Lượt học lấy từ sự kiện Flashcard, Quiz và Game đã ghi nhận, gồm kết quả tự đánh giá Flashcard. Tỷ lệ quay lại ngày kế tiếp dùng những ngày đã quan sát trọn ngày kế tiếp. Điểm trung bình của game lấy tổng điểm các màn được chấm trong kỳ chia cho số lượt chơi có màn đã chấm. Thời điểm bắt đầu lượt chơi và thời điểm chấm màn có thể thuộc hai ngày khác nhau.

Người dùng tải theo nhóm 99 bản ghi và lấy thêm 1 để xác định nhóm tiếp theo. Tìm kiếm và lọc chỉ áp dụng cho nhóm hiện tại. Từ vựng và chủ đề lọc trên trình duyệt. Lịch sử quiz lọc và phân trang trên backend, còn bảng tổng hợp quiz hiển thị toàn bộ lịch sử.

Token giữ trong sessionStorage của tab, xóa khi đăng xuất hoặc backend trả 401/403. Backend kiểm tra quyền trên mọi API quản trị. Không lưu mật khẩu. Dữ liệu được escape khi hiển thị. Không có dữ liệu mẫu hoặc thao tác ghi khi mở trang; dữ liệu thay đổi khi lưu biểu mẫu hoặc xác nhận xóa.

Khi sửa từ vựng, có thể quản lý từng nghĩa tiếng Việt, định nghĩa tiếng Anh, câu ví dụ và bản dịch. Mỗi từ cần giữ ít nhất một nghĩa. Thay đổi áp dụng khi bấm **Lưu thay đổi**. API vẫn nhận dạng dữ liệu sửa nghĩa và ví dụ chính từ các bản Android cũ.

## Quản lý tài khoản người học

Trước khi chạy phiên bản này, trong `backend` chạy `python -m alembic upgrade head` (migration `0010_user_management`), sau đó khởi động lại backend và server web.

- Trạng thái tài khoản hiển thị Hoạt động / Đã khóa. Chỉ ADMIN được xem chi tiết hoặc quản lý tài khoản; chỉ tài khoản USER được khóa/xóa, tài khoản ADMIN được bảo vệ cả ở API.
- Khóa giữ tiến độ nhưng chặn đăng nhập và mọi request có xác thực của người học. Mỗi lần đổi trạng thái thu hồi phiên cũ; mở khóa yêu cầu đăng nhập mới. Request đã được xác thực và đang xử lý trước lúc khóa có thể hoàn tất.
- Xóa yêu cầu nhập đúng username và xác nhận. API kiểm tra lại username trước khi xóa. Database xóa dây chuyền bộ sưu tập, tiến độ, sự kiện học, quiz/đáp án, game/màn chơi, thông báo và bản ghi ảnh; giữ kho từ và dữ liệu người khác. Đây là xóa vĩnh viễn. File ảnh đã tải lên Cloudinary chưa được xóa tự động vì database hiện chưa lưu public_id; dữ liệu cục bộ trên thiết bị không bị xóa từ xa.
- Nút Tiến độ hiển thị CEFR, ngày tham gia, mục tiêu/ngày, streak, từ đã lưu/đã nhớ/đến hạn, quiz hoàn thành, số lượt game và điểm, hoạt động 7 ngày theo UTC+7, số lần đúng/sai và lịch ôn từng từ. Chưa có dữ liệu sẽ hiển thị trạng thái trống.

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
