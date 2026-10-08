# LensLearn Android

Mở **folder frontend** bằng Android Studio. Kotlin + native Views/XML, AndroidX Navigation, Retrofit, JWT và Text-to-Speech.

Hướng dẫn đầy đủ PostgreSQL → Python backend → Android, migration, API, kiểm thử và các luồng chức năng nằm trong [README ở gốc dự án](../README.md).

Android lấy hồ sơ, chủ đề, từ vựng, bộ sưu tập, Flashcard, Quiz và tiến độ qua API. Backend chấm Quiz và lưu kết quả trong PostgreSQL. SharedPreferences giữ phiên, cache theo tài khoản và yêu cầu chờ gửi lại khi mất mạng.

`data/remote/RetrofitClient.kt` dùng `http://127.0.0.1:8000/`. Chạy backend và `adb reverse tcp:8000 tcp:8000` trước khi Run app. Cấu hình Gradle hiện yêu cầu JVM 25 và compile SDK 37; dùng wrapper của repo.

Camera/nhận diện và quản trị hiện là giao diện mẫu; YOLO, thông báo theo lịch và SRS còn cần tích hợp. Quiz hình ảnh dùng biểu tượng/nghĩa tiếng Việt; Quiz nghe cần giọng TTS tiếng Anh trên thiết bị.

APK debug: `app/build/outputs/apk/debug/app-debug.apk`.
