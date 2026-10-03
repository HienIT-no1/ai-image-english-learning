# LensLearn — English Learning App

Giai đoạn 1–2: giao diện Android **Kotlin + XML/native Views**, điều hướng AndroidX Navigation và dữ liệu mẫu lưu trên máy. Giữ nguyên cấu hình Gradle/SDK của project hiện có.

## Chạy trong Android Studio

1. Mở thư mục `EnglishLearningApp` và chờ Gradle Sync.
2. Chọn emulator hoặc thiết bị Android từ API 24 trở lên.
3. Run cấu hình `app`.
4. Bấm **Khám phá bằng hồ sơ mẫu**, chọn trình độ/mục tiêu rồi bấm **Bắt đầu khám phá**. Màn đăng nhập/đăng ký chỉ kiểm tra định dạng đầu vào để thử giao diện; không có xác thực thật.

APK debug: `app/build/outputs/apk/debug/app-debug.apk`.

## Cấu trúc & vai trò

| File/thư mục | Vai trò |
|---|---|
| `MainActivity.kt` | Khung app, thanh điều hướng 5 tab, xử lý system bars/bàn phím và Text-to-Speech |
| `res/layout/activity_main.xml` | NavHost và thanh điều hướng dưới |
| `res/layout/fragment_screen.xml` | Khung màn hình cuộn, dùng chung cho các Fragment |
| `res/navigation/nav_graph.xml` | 19 đích điều hướng, đăng nhập là điểm bắt đầu |
| `ui/ScreenUi.kt` | Thành phần native dùng chung: tiêu đề, thẻ, nút Material, ô nhập, danh sách từ và thanh tiến độ |
| `ui/AccountScreens.kt` | Đăng nhập/đăng ký mẫu, chọn trình độ, hồ sơ, cài đặt |
| `ui/HomeScreens.kt` | Trang chủ và tiến độ học tập |
| `ui/RecognitionScreens.kt` | Camera, thư viện ảnh và kết quả nhận diện mẫu |
| `ui/VocabularyScreens.kt` | Bộ sưu tập, tìm kiếm, chủ đề, chi tiết từ, lịch sử |
| `ui/PracticeScreens.kt` | Flashcard, 4 dạng Quiz, kết quả Quiz |
| `ui/AdminScreens.kt` | Tổng quan và thêm/sửa/xóa các danh sách quản trị mẫu |
| `data/model/Word.kt`, `Topic.kt` | Model từ vựng và chủ đề |
| `data/mock/MockData.kt` | 12 từ có IPA, nghĩa, câu ví dụ; 4 chủ đề |
| `data/local/LearningStore.kt` | SharedPreferences: từ đã lưu, từ đã nhớ, tiến độ, hồ sơ và lịch sử |
| `res/values/colors.xml`, `ui/ScreenUi.kt` | Tông nền xanh tím đậm; nhấn xanh dương, tím, xanh lá |

Các màn hình dùng XML làm khung và dựng nội dung bằng native Views trong Fragment để tái sử dụng bố cục. Không sử dụng Compose hoặc WebView. Những layout rỗng cũ và các lớp server/database/repository chưa triển khai được giữ lại để phát triển tiếp.

## Luồng điều hướng

```text
Đăng nhập / Đăng ký mẫu → Chọn trình độ, mục tiêu → Trang chủ
  ├─ Nhận diện → Chụp / chọn ảnh → Kết quả mẫu → Chi tiết từ → Lưu từ
  ├─ Từ vựng → Tìm kiếm / lọc → Chi tiết từ → Flashcard
  │           └─ Khám phá chủ đề → Danh sách từ của chủ đề
  ├─ Luyện tập → Flashcard → Tự đánh giá → Hoàn thành
  │            └─ Quiz (ảnh / từ / nghe / điền từ / tổng hợp) → Kết quả
  └─ Hồ sơ → Tiến độ / Lịch sử / Cài đặt / Quản trị mẫu / Đăng xuất
              └─ Quản trị mẫu → Người dùng / Từ / Chủ đề / Quiz / Nội dung
```

Android Back quay về màn trước. Bài Quiz yêu cầu xác nhận trước khi thoát. Chuyển tab quay về Trang chủ trong back stack để tránh tích lũy nhiều màn tab. Flashcard và Quiz giữ vị trí, mặt thẻ/đáp án và điểm khi Activity được tạo lại.

## Những gì dùng được ở phiên bản này

- Tìm kiếm tiếng Anh/nghĩa tiếng Việt, lọc từ đã lưu hoặc chủ đề; lưu/bỏ lưu từ.
- Chụp ảnh qua ứng dụng camera với FileProvider, chọn ảnh bằng Android document picker và xem trước ảnh.
- Phát âm từ và câu ví dụ bằng Text-to-Speech trên thiết bị. Cần cài giọng tiếng Anh; app thông báo nếu giọng đọc chưa sẵn sàng.
- Flashcard dùng bộ từ đã lưu; người học tự đánh giá đã nhớ/cần ôn. Xử lý cả bộ từ trống và kết thúc bộ thẻ.
- Quiz có 4 kiểu câu hỏi và bài tổng hợp 8 câu; kiểm tra đáp án, khóa câu đã trả lời, phản hồi và tính điểm thật.
- Mỗi lần tự đánh giá Flashcard hoặc trả lời Quiz tính một lượt luyện tập; mục tiêu ngày tính theo lượt, không phải số từ duy nhất. Streak tính từ ngày có luyện tập thực tế.
- Tiến độ, bộ sưu tập và lịch sử tồn tại sau khi đóng app; đăng xuất không xóa dữ liệu trên máy.
- Admin thử thêm/sửa/xóa các mục mẫu, có xác nhận xóa. Dữ liệu Admin độc lập với kho từ học tập.

## Giới hạn rõ ràng

- **Chưa có backend, database hoặc Google Cloud Vision.** Không upload ảnh, không gọi API và không đặt khóa AI trong app.
- Nhận diện luôn trả 3 từ **Apple, Book, Coffee**, bất kể ảnh được chọn. Giao diện và lịch sử đều ghi rõ dữ liệu mẫu. Hình trong Flashcard/Quiz là emoji minh họa.
- Không có tài khoản/phân quyền thật. Hồ sơ và dữ liệu học dùng chung một bộ dữ liệu trên thiết bị. Email/mật khẩu không được lưu.
- Quản trị là bản thử giao diện, chưa chỉnh sửa dữ liệu từ vựng học tập hoặc thống kê toàn hệ thống.
- Nhắc học mới là tùy chọn lưu trên máy; chưa có thông báo theo lịch. Chưa triển khai thuật toán SRS.

## Kiểm tra

```powershell
# JAVA_HOME trỏ tới JDK của Android Studio nếu cần.
.\gradlew.bat assembleDebug lintDebug testDebugUnitTest --no-configuration-cache
# Khi emulator/thiết bị đang chạy:
.\gradlew.bat connectedDebugAndroidTest --no-configuration-cache
```

`LearningFlowTest` kiểm tra hành trình hồ sơ mẫu → lưu/bỏ lưu từ → Flashcard → hoàn thành Quiz; xác minh dữ liệu lưu trên máy, streak và giữ đáp án sau khi Activity được tạo lại. Kiểm thử giao diện xóa dữ liệu hồ sơ mẫu trước khi chạy; chỉ chạy trên emulator hoặc thiết bị kiểm thử.

## Giai đoạn tiếp theo

Xây Spring Boot + PostgreSQL, thống nhất DTO và REST API trước khi triển khai các lớp `data/remote`/`data/repository`. Sau đó thay nguồn dữ liệu mẫu bằng repository thực; gửi ảnh đến backend để backend gọi Google Cloud Vision. Bổ sung xác thực/phân quyền, dữ liệu riêng cho từng tài khoản, nội dung quản trị thật, SRS và thông báo.
