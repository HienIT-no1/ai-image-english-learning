# LensLearn — Android + Python + PostgreSQL

Ứng dụng học từ vựng tiếng Anh. Android viết bằng Kotlin, backend dùng FastAPI/SQLAlchemy, database dùng PostgreSQL. Những chức năng đã nối server sử dụng dữ liệu thật trong PostgreSQL.

## 1. Các luồng hiện có

| Luồng | Trạng thái | Dữ liệu lưu ở đâu? |
|---|---|---|
| Đăng ký, đăng nhập, kiểm tra token, đăng xuất | Đã nối Android → API → database | `users`; token lưu trên thiết bị |
| Chủ đề → danh sách từ → chi tiết nghĩa, ví dụ | Đã nối đầy đủ | `topics`, `vocabulary_topics`, `vocabularies`, bảng nghĩa/ví dụ |
| Lưu/bỏ lưu từ, khôi phục bộ sưu tập theo tài khoản | Đã nối đầy đủ | `collections`, `collection_words` |
| Chọn trình độ/mục tiêu lần đầu; sửa hồ sơ, cài đặt | Đã nối đầy đủ | `users` |
| Flashcard → tự đánh giá → cập nhật tiến độ | Đã nối đầy đủ | `learning_events`, `learning_progress` |
| Quiz → tạo bài → trả lời → chấm điểm → hoàn thành | Đã nối đầy đủ | `quiz_attempts`, `quiz_answers`, `learning_events`, `learning_progress` |
| Trò chơi Bắn chữ → chọn nguồn → chơi → lưu kết quả → màn tiếp | Đã nối Android → API → PostgreSQL | `game_runs`, `game_rounds`, `learning_events`, `learning_progress` |
| Trang chủ, tiến độ, lượt học, mục tiêu, streak | Lấy số liệu từ API/database | Tổng hợp dữ liệu của tài khoản |
| Chụp/chọn ảnh, nhận diện và lịch sử nhận diện | Giao diện mẫu; chưa nối YOLO | Cần triển khai backend nhận ảnh/nhận diện |
| Phân quyền và quản trị | Đã nối Android → API có kiểm tra ADMIN → database | Xem người dùng; thêm/sửa chủ đề và từ; xóa chủ đề trống |
| Nhắc học, lịch ôn SRS | Chưa triển khai | Mới lưu tùy chọn nhắc học; chưa lên lịch thông báo |

Quiz hình ảnh hiện dùng **biểu tượng và nghĩa tiếng Việt**, chưa dùng ảnh thật từ AI. Quiz nghe dùng Text-to-Speech trên thiết bị. Bài tổng hợp yêu cầu 8 câu; nếu kho từ có nghĩa chỉ có ít hơn 8 từ, server trả số câu thực tế. Trình độ và mục tiêu đã được lưu; Quiz hiện chưa tự điều chỉnh độ khó theo trình độ. Trò Bắn chữ ngẫu nhiên lọc cấp độ từ theo CEFR; tốc độ rơi tăng theo màn và có giới hạn.

## 2. Cấu trúc dự án và trách nhiệm

```text
ai-image-english-learning/
├── backend/
│   ├── main.py                  # Tạo FastAPI app và đăng ký router
│   ├── app/
│   │   ├── core/                # .env, database session, JWT, mật khẩu
│   │   ├── models/              # SQLAlchemy: ánh xạ bảng PostgreSQL
│   │   ├── schemas/             # Pydantic: kiểm tra request, định dạng response
│   │   ├── routers/             # Địa chỉ API, HTTP, xác thực
│   │   ├── services/            # Quy tắc nghiệp vụ, chấm Quiz, giao dịch
│   │   └── repositories/        # Đọc/ghi và tổng hợp dữ liệu
│   ├── migrations/              # Các phiên bản thay đổi schema bằng Alembic
│   ├── tests/                   # Kiểm thử API với PostgreSQL tạm
│   ├── seed_demo.py             # Thêm từ mẫu cho database mới
│   └── .env.example             # Mẫu cấu hình; .env thật không đưa lên Git
└── frontend/
    ├── app/src/main/java/com/example/englishlearningapp/
    │   ├── MainActivity.kt      # Khởi tạo repository, phiên, điều hướng, TTS
    │   ├── ui/                  # Màn hình và các trạng thái tải/lỗi/thử lại
    │   └── data/
    │       ├── remote/          # Retrofit, địa chỉ server, xử lý lỗi HTTP
    │       ├── repository/      # Gọi API, cache, bảo vệ dữ liệu theo phiên
    │       ├── model/           # DTO API và model hiển thị
    │       └── local/           # SharedPreferences: phiên/cache/yêu cầu chờ gửi
    └── settings.gradle.kts      # Mở folder này bằng Android Studio
```

Ví dụ khi bấm **Đã nhớ**:

```text
FlashcardFragment
  → LearningRepository tạo request kèm UUID của lượt học
  → Retrofit POST /learning/me/reviews + Bearer token
  → router xác thực người học
  → service kiểm tra từ
  → repository ghi learning_events, cập nhật learning_progress
  → PostgreSQL commit
  → API trả thống kê mới
  → Android cập nhật màn hình
```

`schemas` xác định dữ liệu được phép gửi, `models` mô tả bảng, `services` quyết định xử lý ra sao, `repositories` thực hiện truy vấn. Router hồ sơ hiện xử lý trực tiếp phần cập nhật đơn giản. Android không kết nối trực tiếp PostgreSQL; chỉ backend biết thông tin kết nối database.

## 3. Phần mềm và môi trường cần có

- **Git** để kéo/đẩy code. GitHub Desktop là giao diện tùy chọn.
- **Python** và môi trường `.venv`. Máy phát triển đã chạy kiểm thử bằng Python 3.14; thư viện nằm trong `backend/requirements.txt`.
- **PostgreSQL** đang chạy. Máy phát triển dùng PostgreSQL 17. **pgAdmin** để tạo database/xem bảng; đóng pgAdmin không đồng nghĩa tắt dịch vụ PostgreSQL.
- **VS Code** để sửa Python và chạy terminal. Không bắt buộc phải mở VS Code thì backend mới chạy được.
- **Android Studio**, Android SDK, Platform-Tools (`adb`) và emulator hoặc điện thoại USB. Cấu hình hiện tại dùng compile SDK 37, Gradle wrapper của repo và Gradle JVM 25 (`frontend/gradle/gradle-daemon-jvm.properties`). Máy này dùng JBR đi kèm Android Studio. Android tối thiểu API 24.

Các đường dẫn `D:\PhanMem\...` dưới đây là của máy đang phát triển. Máy khác cần đổi theo nơi đã cài phần mềm.

## 4. Chạy lần đầu: PostgreSQL → backend → Android

### Bước 1 — PostgreSQL/pgAdmin

1. Mở pgAdmin và kết nối server PostgreSQL trên máy, cổng thường dùng là `5432`.
2. Nếu chưa có, tạo database tên `english_learning`: Databases → Create → Database.
3. Nếu database đã import dữ liệu dự án, giữ database đó và chuyển sang bước 2. Không cần import lại mỗi lần cập nhật code.

### Bước 2 — VS Code và môi trường Python

VS Code → **Open Folder** → `ai-image-english-learning`. Terminal → **New Terminal**, chọn PowerShell.

Vào backend từ thư mục gốc dự án:

```powershell
cd backend
```

Chỉ tạo môi trường nếu chưa có `.venv`:

```powershell
py -m venv .venv
```

Cài thư viện sau khi clone hoặc khi requirements thay đổi:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Chỉ copy mẫu cấu hình nếu chưa có `.env`:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và sửa theo database của máy:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/english_learning
JWT_SECRET_KEY=YOUR_RANDOM_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Thay `YOUR_PASSWORD`, đặt secret ngẫu nhiên. Nếu mật khẩu chứa ký tự đặc biệt như `@`, cần URL-encode phần mật khẩu trong connection URL. `.env` đã được ignore; không đưa mật khẩu/secret lên GitHub.

### Bước 3 — Cập nhật bảng bằng migration

Chạy trong **backend**:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Kiểm tra phiên bản:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

Phiên bản hiện tại: `0006_word_shooter`. Lệnh upgrade chỉ áp dụng các bước còn thiếu; chạy lại không tạo trùng bảng/dữ liệu. Nếu database mới chưa có từ để học:

```powershell
.\.venv\Scripts\python.exe seed_demo.py
```

Seed thêm 4 từ mẫu, nghĩa, ví dụ và gắn chủ đề. Chạy lại không tạo trùng hoặc ghi đè nội dung từ đã có. Database dự án đã import có thể dùng kho từ sẵn có.

### Bước 4 — Chạy backend

Giữ terminal ở **backend**:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

- `.venv\Scripts\python.exe`: dùng Python và thư viện riêng của dự án, không cần kích hoạt venv.
- `-m uvicorn`: chạy thư viện server Uvicorn bằng Python đó.
- `main:app`: tìm biến `app` trong `main.py`; file này có `app = FastAPI(...)`.
- `--host 127.0.0.1 --port 8000`: nhận kết nối trên máy tính ở cổng 8000.

Lệnh phải chạy trong backend vì cấu hình đọc `.env` tại thư mục đang làm việc. Khi phát triển có thể thêm `--reload` để tự khởi động lại khi sửa Python. Giữ terminal này mở.

Mở [kiểm tra server](http://127.0.0.1:8000/health) và [Swagger thử API](http://127.0.0.1:8000/docs). `/health` xác nhận server hoạt động; thử `/topics` hoặc đăng nhập để kiểm tra truy vấn database. Tắt server bằng **Ctrl+C** trong terminal đang chạy.

### Bước 5 — Android Studio và adb reverse

1. Android Studio → **Open** → chọn `ai-image-english-learning/frontend`.
2. Chờ Gradle sync. Nếu hỏi Gradle JDK, chọn JBR/JDK 25 phù hợp cấu hình dự án.
3. Device Manager → bật emulator, hoặc kết nối điện thoại qua USB và bật USB debugging.
4. Mở **terminal thứ hai**, giữ terminal backend đang chạy. Liệt kê thiết bị:

```powershell
& "D:\PhanMem\AndroidStudioSDK\platform-tools\adb.exe" devices
```

Chuyển cổng của thiết bị về backend trên máy tính:

```powershell
& "D:\PhanMem\AndroidStudioSDK\platform-tools\adb.exe" reverse tcp:8000 tcp:8000
```

Nếu có nhiều thiết bị:

```powershell
& "D:\PhanMem\AndroidStudioSDK\platform-tools\adb.exe" -s emulator-5554 reverse tcp:8000 tcp:8000
```

5. Nhấn **Run ▶** trong Android Studio để cài/chạy app. Bật emulator chỉ mở máy Android; Run mới build/cài/mở ứng dụng.
6. Đăng ký tài khoản → chọn trình độ/mục tiêu → vào trang chủ. Tài khoản đã hoàn thành hồ sơ sẽ bỏ qua bước chọn ban đầu.

`RetrofitClient.kt` dùng `http://127.0.0.1:8000/`. Trên Android, địa chỉ này là chính thiết bị; `adb reverse` chuyển yêu cầu đó về cổng 8000 của máy tính. Chạy lại reverse sau khi khởi động lại emulator/rút cáp USB.

## 5. Mỗi lần mở lại dự án

Không cần tạo venv, tạo database hoặc seed lại. Sau khi kéo code có migration mới, chạy upgrade trước khi khởi động backend.

1. PostgreSQL đang chạy; pgAdmin chỉ cần mở nếu muốn xem dữ liệu.
2. VS Code → terminal trong backend → `alembic upgrade head` → lệnh Uvicorn ở bước 4.
3. Android Studio → mở frontend → bật emulator.
4. Terminal thứ hai → `adb reverse tcp:8000 tcp:8000` bằng đường dẫn ở bước 5.
5. Run app. Đăng nhập lại nếu token hết hạn.

## 6. Các API và quy tắc của luồng

Các API có `/me` và `/quizzes` yêu cầu `Authorization: Bearer <token>`. Backend lấy chủ sở hữu từ token, không nhận `user_id` do Android tự chọn.

| API | Chức năng |
|---|---|
| `POST /auth/register`, `POST /auth/login` | Tạo tài khoản, lấy token |
| `GET /users/me` | Kiểm tra phiên, lấy hồ sơ |
| `PATCH /users/me` | Lưu tên, CEFR, mục tiêu, tùy chọn nhắc học; đánh dấu hoàn thành hồ sơ |
| `GET /topics`, `GET /topics/{id}/vocabularies` | Chủ đề và kho từ theo chủ đề; công khai |
| `GET /vocabularies`, `GET /vocabularies/{id}` | Kho từ/chi tiết từ; công khai |
| `GET /collections/me` | Bộ sưu tập mặc định và các từ đã lưu |
| `PUT`, `DELETE /collections/me/words/{id}` | Lưu/bỏ lưu từ; gửi lại không tạo trùng |
| `GET /learning/me` | Tiến độ, 7 ngày gần đây, streak, kết quả Quiz |
| `POST /learning/me/reviews` | Lưu một lượt tự đánh giá Flashcard |
| `POST /quizzes` | Tạo/khôi phục bài theo `client_session_id` |
| `GET /quizzes/{id}` | Đọc bài và các đáp án đã lưu của chủ sở hữu |
| `POST /quizzes/{id}/answers` | Server chấm và lưu một đáp án theo thứ tự |
| `POST /quizzes/{id}/complete` | Hoàn thành bài khi tất cả câu đã được trả lời |
| `POST /quizzes/{id}/abort` | Dừng bài; giữ các câu đã trả lời |

### Phiên và dữ liệu theo tài khoản

Mở app → kiểm tra `/users/me` → tải bộ sưu tập, gửi lại yêu cầu học còn chờ, tải tiến độ → vào trang chủ/onboarding. Mất mạng hiển thị **Thử lại**, giữ token. Token không hợp lệ/hết hạn trả 401 thì app xóa phiên và mở đăng nhập. Chưa có refresh token.

Token lưu trong `learning_demo`; cache và yêu cầu còn chờ tách theo `learning_user_<user_id>`. Đăng xuất giữ dữ liệu server. Phản hồi trễ của tài khoản A bị bỏ qua khi đã sang B; mỗi request cá nhân gắn token của phiên tạo request. Tiến độ và bộ sưu tập tải lại từ PostgreSQL khi đăng nhập trên thiết bị khác.

Dữ liệu luyện tập mẫu cũ trên điện thoại được giữ làm dữ liệu cũ, không tự chuyển thành kết quả server vì không đủ thông tin đáng tin cậy về từng lượt. Sau khi tải API, số liệu server là nguồn chính thức.

### Hồ sơ và mục tiêu

Ví dụ request PATCH:

```json
{"full_name":"Hiếu","cefr_level":"A2","daily_goal":10,"reminders_enabled":false}
```

Tên không được trống; CEFR hỗ trợ A1/A2/B1/B2; mục tiêu từ 1 đến 200 lượt/ngày, UI có 5/10/15/20. Giữ tương thích schema cũ: A1/A2 → `BEGINNER`, B1 → `INTERMEDIATE`, B2 → `ADVANCED`. `cefr_level` lưu đúng lựa chọn, không làm mất A2.

### Flashcard và thống kê

Mỗi thẻ có một `event_key` UUID. Chỉ chuyển sang thẻ tiếp theo khi server xác nhận đã lưu. Mất mạng có **Thử lưu lại**; app giữ request để gửi lại cùng UUID. PostgreSQL ràng buộc duy nhất `(user_id, event_key)`, nên trường hợp server đã lưu nhưng app chưa nhận response không bị tính thêm lượt. Dùng lại UUID với nội dung khác trả 409.

- **Đã nhớ**: trạng thái từ chuyển `MASTERED`; **Cần ôn lại**: `LEARNING`. Đây là người học tự đánh giá.
- `learning_progress` tổng hợp số lần đúng/sai/luyện tập của từng từ.
- `learning_events` lưu từng lượt, dùng cho thống kê ngày và streak.
- Một thẻ đã đánh giá hoặc một câu Quiz đã gửi tính **một lượt**, kể cả trả lời sai. Lưu từ, lật thẻ và nghe phát âm không tính lượt.
- Ngày học tính theo **Asia/Ho_Chi_Minh (UTC+7)**. Streak còn giữ chuỗi đến hôm qua khi hôm nay chưa học; nếu bỏ trọn một ngày thì chuỗi hiện tại về 0.
- “Cần ôn tập” là từ đã lưu chưa có trạng thái `MASTERED`; hiện chưa phải lịch ôn SRS.
- Tổng lượt và Quiz cũ trong PostgreSQL vẫn được giữ. Biểu đồ ngày dựa vào `learning_events` mới; migration không tự đoán ngày của các lượt cũ.

### Quiz và tiếp tục bài

Server lấy từ có nghĩa trong kho dữ liệu, ưu tiên từ đã lưu. Câu hỏi và phương án được chụp lại trong `question_payload`, nên sửa kho từ trong lúc làm bài không tự đổi đề đang làm. Các lựa chọn cùng câu tránh trùng nhãn hiển thị.

Android gửi ID câu hỏi và lựa chọn, hoặc chuỗi tiếng Anh cho câu điền từ. Server xác định đúng/sai, tăng điểm và lưu `quiz_answers`; Android không gửi điểm hay cờ `is_correct`. Điền từ bỏ khoảng trắng đầu/cuối và không phân biệt hoa/thường. Mỗi câu chỉ được ghi một đáp án; gửi lại cùng đáp án trả kết quả cũ, đổi đáp án đã ghi trả 409.

Câu hỏi chứa dữ liệu từ để hiển thị và phát âm TTS. Đây là Quiz luyện tập có phản hồi đáp án; chưa phải bài thi bảo mật chống xem đáp án qua API.

Thoát/đóng app giữa bài → **Luyện tập → Tiếp tục bài Quiz đang làm**. Android giữ khóa phiên của bài theo tài khoản trên thiết bị; server giữ các câu đã gửi. Tự động tiếp tục hiện áp dụng trên thiết bị có khóa phiên, chưa có màn hình liệt kê bài chưa hoàn thành ở thiết bị khác. Bắt đầu dạng khác dừng bài cũ nhưng giữ các lượt đã học. Bài chưa hoàn thành vẫn có lượt học; thống kê “Bài hoàn thành/Độ chính xác Quiz” chỉ tính bài đã complete. Quiz không tự đổi trạng thái `MASTERED` đã đánh giá bằng Flashcard.

## 7. Migration khi làm việc nhóm

| Revision | Thay đổi |
|---|---|
| `0001_legacy` | Tạo 11 bảng cũ trên database mới; tiếp nhận schema cũ đủ bảng/cột và giữ dữ liệu |
| `0002_topics` | Thêm chủ đề và bảng liên kết, 6 chủ đề, gắn các từ quen thuộc sẵn có |
| `0003_collection` | Thêm bộ sưu tập mặc định duy nhất theo người dùng; tập hợp từ cũ vào bộ mặc định và giữ bộ nguồn |
| `0004_learning` | Thêm CEFR/onboarding/tùy chọn nhắc học, nhật ký lượt học, khóa phiên và đề Quiz, khóa câu/đáp án |
| `0005_admin_roles` | Thêm role USER/ADMIN, tất cả tài khoản cũ mặc định USER; không tự cấp Admin |
| `0006_word_shooter` | Thêm lượt chơi, màn chơi; cho phép learning event loại GAME; giữ dữ liệu cũ |

Bạn cùng nhóm kéo code → cài requirements → cấu hình `.env` → `alembic upgrade head`. Database mới có thể seed; không cần gửi/import lại SQL mỗi lần đổi bảng. Migration không thay thế việc sao lưu dữ liệu.

Khi thay model/schema, tạo revision mới và đọc kỹ trước khi áp dụng. Không sửa revision mà nhóm đã chạy:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe your schema change"
```

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

```powershell
.\.venv\Scripts\python.exe -m alembic check
```

Autogenerate hiện quản lý `topics`, `vocabulary_topics`, `collections`, `collection_words`, `learning_progress`, `learning_events`, `quiz_attempts`, `quiz_answers`, `game_runs`, `game_rounds`. Một số model legacy chưa mô tả toàn bộ schema, nên các bảng khác (gồm `users`) cần migration thủ công hoặc hoàn thiện mapping trước khi đưa vào `MANAGED_TABLES` trong `migrations/env.py`.

Baseline kiểm tra đủ bảng/cột, không xác thực mọi kiểu/constraint của schema tự sửa. Schema legacy chỉ có một phần bị từ chối; cần sửa/import đủ schema trước. Migration cần kết nối PostgreSQL, chưa hỗ trợ xuất SQL offline. Downgrade các revision thêm bảng/cột có thể xóa dữ liệu của phần đó; baseline từ chối downgrade để bảo vệ dữ liệu đã tiếp nhận.

## 8. Kiểm thử

### Backend

Trong backend, cài thư viện kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Chạy:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Test tạo các database tạm `test_topic_<uuid>` rồi xóa, không chèn fixture vào database ứng dụng. Tài khoản kiểm thử cần quyền tạo database; có thể đặt `TEST_DATABASE_URL` riêng. Bộ test gồm migration/schema legacy/seed, chủ đề, token hết hạn, bộ sưu tập, cập nhật hồ sơ, lượt học đồng thời không trùng, cả 5 dạng Quiz, tiếp tục bài, truy cập chéo tài khoản, đáp án sai và điểm do server tính.

### Android

Trong frontend, build bằng Gradle wrapper:

```powershell
$env:JAVA_HOME="D:\PhanMem\Android studio\jbr"
```

```powershell
$env:ANDROID_HOME="D:\PhanMem\AndroidStudioSDK"
```

```powershell
.\gradlew.bat :app:assembleDebug :app:assembleDebugAndroidTest --console=plain
```

APK debug nằm ở `frontend/app/build/outputs/apk/debug/app-debug.apk`. Kiểm thử instrumentation hiện kiểm tra app yêu cầu đăng nhập khi không có token, sau tạo lại Activity, và kiểm tra tên đăng nhập không hợp lệ. Chạy trên emulator kiểm thử. Bộ chạy Android trên cấu hình hiện tại tự gỡ app sau khi kiểm thử, có thể xóa phiên/cache/lịch sử mẫu trên emulator; sau đó Run lại app và đăng nhập để tải dữ liệu server. PostgreSQL không bị reset bởi bộ kiểm thử Android:

```powershell
.\gradlew.bat :app:connectedDebugAndroidTest --console=plain
```

### Tự kiểm tra một luồng đầy đủ

1. Đăng ký A → chọn A2 và mục tiêu 5 → trang chủ.
2. Từ vựng → Tất cả → cat → Lưu vào bộ sưu tập.
3. Luyện tập → Flashcard → Lật thẻ → Đã nhớ. Mở Tiến độ: có 1 lượt, 1 từ đã nhớ, 1 ngày liên tiếp.
4. Ôn lại → Cần ôn lại: lượt tăng, từ chuyển cần ôn. Tắt kết nối backend thử lưu: có thử lại, chưa tự chuyển thẻ; nối lại và thử lưu lại.
5. Hồ sơ → Cài đặt → đổi tên/mục tiêu → Lưu. Đóng/mở app, hồ sơ vẫn giữ.
6. Quiz → trả lời đúng một câu, sai một câu → xem phản hồi. Thoát/đóng app giữa bài → Luyện tập → tiếp tục đúng bài ở câu chưa trả lời.
7. Hoàn thành Quiz → kết quả đúng bằng các câu đã trả lời; Tiến độ tăng bài hoàn thành và tổng lượt.
8. Đăng xuất A → đăng ký/đăng nhập B: B có bộ sưu tập và tiến độ riêng. Quay lại A lấy lại dữ liệu A.

Xem dữ liệu trong pgAdmin → database → Query Tool, dùng tên tài khoản thử của bạn:

```sql
SELECT user_id, username, full_name, cefr_level, daily_goal, onboarding_completed
FROM users;
SELECT p.* FROM learning_progress p JOIN users u USING(user_id)
WHERE u.username = 'YOUR_TEST_USERNAME';
SELECT e.* FROM learning_events e JOIN users u USING(user_id)
WHERE u.username = 'YOUR_TEST_USERNAME' ORDER BY event_id DESC;
SELECT q.attempt_id, q.quiz_type, q.total_questions, q.correct_answers, q.completed_at
FROM quiz_attempts q JOIN users u USING(user_id)
WHERE u.username = 'YOUR_TEST_USERNAME' ORDER BY q.attempt_id DESC;
```

Kiểm tra trên máy ngày 08/10/2026: 18 test backend đã qua, build Android và instrumentation đã qua. Kiểm tra trực tiếp trên emulator đã xác nhận hồ sơ, Flashcard, lưu lại khi mất mạng, sửa cài đặt, tiếp tục Quiz sau đóng/mở app, điểm do server tính và dữ liệu riêng giữa hai tài khoản. Các tài khoản thử đã được xóa sau kiểm tra.

## 9. Lỗi thường gặp

- **`git` không được nhận diện:** mở lại terminal sau khi cài Git; kiểm tra `git --version`. VS Code đang mở từ trước khi cài có thể cần khởi động lại.
- **Thiếu DATABASE_URL/JWT khi chạy:** terminal phải ở backend và backend có `.env` đúng giá trị.
- **Database connection refused:** kiểm tra dịch vụ PostgreSQL, hostname/cổng trong `.env`.
- **Password authentication failed:** sửa tài khoản/mật khẩu database trong `.env`.
- **Cột/bảng không tồn tại sau kéo code:** chạy `alembic upgrade head` bằng đúng `.env` của database đang dùng, rồi khởi động lại backend.
- **WinError 10048/cổng 8000 đang dùng:** đã có chương trình chiếm cổng. Dừng server cũ bằng Ctrl+C. Có thể xem PID bằng `Get-NetTCPConnection -LocalPort 8000 -State Listen`; chỉ dừng PID sau khi xác định đúng backend cần tắt.
- **App không kết nối được server:** thử `/docs` trên máy tính, `adb devices`, rồi chạy lại `adb reverse`. Đảm bảo URL/cổng Android và Uvicorn đều là 8000.
- **Hết hạn phiên:** đăng nhập lại. Đăng xuất không xóa dữ liệu PostgreSQL.
- **Quiz không có câu hỏi:** kho từ cần có từ và nghĩa; với database mới chạy seed.
- **Không nghe phát âm:** cài/bật giọng tiếng Anh trong Text-to-Speech của Android. Quiz nghe phụ thuộc giọng đọc trên thiết bị.

## 10. Hướng tiếp theo

1. Nhận ảnh → backend gọi YOLO → ánh xạ nhãn thành từ thật → lưu kết quả/lịch sử và thêm từ vào bộ sưu tập.
2. Mở rộng quản trị nghĩa/ví dụ phụ, ảnh minh họa thật và các thao tác quản lý người dùng theo nghiệp vụ.
3. Lịch ôn SRS và nhắc học thực tế; sau đó mở rộng thống kê/lịch sử bài Quiz và danh sách bài chưa hoàn thành ở nhiều thiết bị.


## 11. Phân quyền USER/ADMIN và tạo tài khoản Admin

Admin dùng **màn hình đăng nhập chung trên Android**. Sau đăng nhập hoặc mở lại app, `/users/me` trả role từ database. USER vào học tập/onboarding; ADMIN vào Tổng quan hệ thống, có thể bấm Về trang học tập và mở lại Quản trị hệ thống trong Hồ sơ.

### Quy tắc phân quyền

- Đăng ký công khai luôn tạo `USER`. Gửi `role`, `is_admin` hoặc trường không được phép trong đăng ký/sửa hồ sơ bị từ chối 422.
- Tài khoản Admin được tạo riêng bằng lệnh chạy trên server có quyền truy cập database; không có màn hình đăng ký Admin, không có mật khẩu Admin mặc định.
- Tất cả API `/admin/*` kiểm tra `get_current_admin`. Không có token trả 401; USER trả 403. Kiểm tra này áp dụng cả đọc và ghi.
- Backend đọc role từ PostgreSQL ở mỗi request, không tin role do Android hoặc token tự khai. Thu hồi quyền có hiệu lực ở request tiếp theo dù token cũ chưa hết hạn.
- Role lưu trên Android chỉ dùng điều hướng/hiển thị. Đổi cache trên máy không cấp được quyền API. Đăng xuất xóa role của phiên; đổi tài khoản không giữ giao diện Admin của người trước.
- `/admin/users` chỉ trả ID, tên đăng nhập, email, tên hiển thị và role; không trả password hash, token hay secret. Màn hình người dùng chỉ xem, phân trang 100 tài khoản.

### Cấp tài khoản Admin đầu tiên

Trong terminal PowerShell của VS Code, chuyển vào thư mục backend. Nếu đang ở gốc repo:

```powershell
cd backend
```

Cập nhật schema (database và .env phải đúng):

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Tạo Admin, thay email bên dưới bằng **email thật chưa được dùng cho tài khoản khác**:

```powershell
.\.venv\Scripts\python.exe create_admin.py --username admin --email "email-cua-ban@example.com" --full-name "Quản trị viên"
```

Terminal hỏi mật khẩu và nhập lại để xác nhận. Mật khẩu 8–128 ký tự, không hiện khi gõ; backend băm bằng Argon2. Không đưa mật khẩu vào command line, Git, README hay code Android. Có thể đổi `--username` theo ý bạn.

Nếu tên/email đã tồn tại, lệnh dừng và giữ tài khoản cũ; không tự nâng quyền hoặc đổi mật khẩu người dùng đã có. Chọn tên/email mới để tạo một tài khoản Admin riêng. Không dùng lệnh này như một API công khai.

Sau khi cập nhật backend đang chạy, dừng bằng Ctrl+C và khởi động lại Uvicorn. Run bản Android mới, chạy adb reverse như mục 4. Đăng nhập bằng tên/mật khẩu vừa cấp → Tổng quan hệ thống.

### Các chức năng quản trị đã triển khai

| API | Thao tác |
|---|---|
| `GET /admin/summary` | Số tài khoản/Admin/chủ đề/từ và Quiz hoàn thành |
| `GET /admin/users?offset=0&limit=100` | Xem danh sách người dùng, phân trang |
| `GET`, `POST /admin/topics` | Đọc và thêm chủ đề |
| `PUT /admin/topics/{id}` | Sửa tên, slug, biểu tượng |
| `DELETE /admin/topics/{id}` | Xóa chủ đề trống; chủ đề đang có từ trả 409 |
| `GET`, `POST /admin/vocabularies` | Đọc và thêm từ, nghĩa chính, phiên âm, ví dụ, các chủ đề |
| `PUT /admin/vocabularies/{id}` | Sửa từ, nghĩa/ví dụ chính và các liên kết chủ đề |

Mã chủ đề dùng chữ thường, số và dấu gạch nối, ví dụ `school-items`. Tên/mã bị trùng trả 409. Từ vựng cần từ tiếng Anh và nghĩa tiếng Việt; có thể chọn nhiều chủ đề. Phần sửa chính giữ các nghĩa/ví dụ phụ, definition, quan hệ và lịch sử đã có. Câu ví dụ chính đang tồn tại phải được giữ hoặc sửa, không xóa bằng cách để trống. Thứ tự nghĩa/ví dụ theo ID để nội dung chính hiển thị nhất quán.

Hiện chưa có xóa từ, xóa/khóa tài khoản, cấp/thu hồi role qua app hoặc quản trị nội dung Quiz riêng. Quiz vẫn được tạo từ kho từ thật. Không dùng những chức năng mẫu trước đây để giả lập thao tác trên database.

### Tự thử phân quyền và một luồng quản trị

1. Đăng ký USER → vào Hồ sơ: không có Quản trị hệ thống. Gọi API `/admin/summary` bằng token USER phải trả 403.
2. Chạy lệnh cấp Admin, đăng nhập Admin → xem Tổng quan và Người dùng.
3. Chủ đề → Thêm chủ đề → nhập tên/mã/biểu tượng → Lưu. Mở pgAdmin bảng `topics` hoặc API `/topics` để thấy dữ liệu.
4. Kho từ vựng → Thêm từ → nhập từ/nghĩa/ví dụ → Chọn chủ đề vừa tạo → Lưu. USER mở chủ đề đó sẽ thấy từ mới.
5. Sửa nghĩa chính → USER tải lại danh sách/chi tiết từ để lấy nội dung mới.
6. Thử xóa chủ đề đang có từ: bị từ chối. Bỏ liên kết bằng màn sửa từ rồi có thể xóa chủ đề trống.

Kiểm thử backend có thêm chống tự cấp quyền, từ chối tất cả route quản trị đối với USER/không token, kiểm tra role đang có trong DB, lệnh cấp Admin không đổi tài khoản cũ, giữ các nghĩa/ví dụ phụ và dữ liệu cũ khi migration. Khi kiểm tra thu hồi quyền trong database, chỉ sửa tài khoản kiểm thử đã tạo; không thu hồi tài khoản Admin đang cần dùng.

Kiểm tra ngày 14/10/2026: 24 test backend đã qua; Android assembleDebug thành công. Emulator xác nhận USER không có menu Admin và nhận 403 ở API; Admin đăng nhập chung, thêm/sửa chủ đề và từ thật; thu hồi role khiến token cũ bị từ chối và app trở về USER khi mở lại. Tài khoản/dữ liệu kiểm thử đã được xóa; dữ liệu và SharedPreferences ban đầu được giữ lại.


## 12. Trò chơi Bắn chữ — Android → FastAPI → PostgreSQL

### Cách mở và chơi

Trang chủ hoặc Luyện tập → **Trò chơi** → chọn nguồn từ:

- **Ngẫu nhiên**: từ phù hợp trình độ; một chặng tối đa 5 màn vượt thành công.
- **Theo chủ đề**: chọn một chủ đề, chơi đến khi hoàn thành bộ từ.
- **Ôn từ của bạn**: chọn từ đã lưu, từ khó hoặc kết hợp. Từ khó là từ có lần đánh giá gần nhất sai; dữ liệu cũ chưa có nhật ký dùng số sai lớn hơn số đúng làm dự phòng.

Mỗi màn tối đa **20 từ khác nhau**. Nếu nhóm chỉ còn ít hơn 20 từ, số từ thực tế được ghi trên màn hình, không lặp lại từ đã đúng để bù số lượng. Chỉ các từ có nghĩa và gõ được bằng A–Z được chọn; khoảng trắng, gạch nối và dấu nháy được điền sẵn. Giới hạn 24 chữ cái mỗi từ/cụm từ để phù hợp màn hình điện thoại.

1. Bấm **Tiếp tục** để bắt đầu. Nghĩa tiếng Việt và các ô trống rơi dần xuống.
2. Từ đang ngắm có viền xanh; chạm từ khác để đổi mục tiêu. Sau khi hoàn thành/bỏ lỡ mục tiêu, game ngắm từ gần đáy nhất.
3. Bấm bàn phím A–Z của game hoặc bàn phím vật lý để bắn chữ tiếp theo. Hoàn thành từ sẽ phát âm bằng TTS trên thiết bị.
4. **Gõ sai chữ chỉ hiện hiệu ứng sai**: không trừ lượt, không xóa chữ đúng và không làm đứt combo.
5. Hoàn thành 5 từ liên tiếp bắt đầu combo. Chuỗi tiếp tục 6, 7… đến hết màn; màu đạn và hiệu ứng tăng ở các mốc 5/10/15. Combo 20 có kết quả HOÀN HẢO.
6. **Chạm đáy mới làm đứt combo** và tăng số bỏ lỡ. Được bỏ lỡ 3 từ; lần thứ 4 thua màn và dừng ngay.
7. Tạm dừng hoặc chuyển ứng dụng dừng đồng hồ rơi. Nút **Tiếp tục / xem kết quả lượt trước** phục hồi lượt trên cùng thiết bị và cùng tài khoản.

### Chuyển màn và tính điểm

- Vượt màn: màn sau gồm từ bỏ lỡ của màn trước + từ chưa chơi, tối đa 20. Các từ đã đúng trong những màn **đã vượt** bị loại khỏi phần còn lại của lượt này.
- Ví dụ: đúng 17, bỏ lỡ 3 → màn sau có 3 từ cần ôn + 17 từ mới nếu đủ kho từ.
- Thua màn: chơi lại chính bộ từ của màn đó, giữ số màn; các kết quả đã gửi vẫn nằm trong lịch sử học.
- Ngẫu nhiên kết thúc sau 5 màn đã vượt hoặc hết bộ từ. Chủ đề/ôn tập kết thúc khi hết từ chưa đúng. Nếu chỉ còn từ sai, màn cuối dùng các từ đó.
- Mỗi từ hoàn thành được 100 điểm, cộng thêm `25 × floor(combo hiện tại / 5)`. Sai chữ không giảm điểm. Tổng điểm lượt chơi cộng điểm của các lần chơi màn, gồm cả lần thua; chưa có bảng xếp hạng thi đấu.
- Tốc độ tăng nhẹ theo màn và đạt trần; từ dài có nhiều thời gian hơn. Màn kết quả cho nghe lại từ bỏ lỡ.

### Chạy trên máy này sau khi kéo code

Trong VS Code, mở repo `ai-image-english-learning`. Terminal PowerShell ở thư mục gốc:

```powershell
cd backend
```

Cập nhật bảng tự động, không import lại database:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Nếu muốn bộ từ khởi đầu để thử các màn 20 từ:

```powershell
.\.venv\Scripts\python.exe seed_game.py
```

Lệnh seed có 100 từ cơ bản thuộc Động vật, Đồ ăn, Đồ vật, Địa điểm và Thiên nhiên. Chạy lại không nhân đôi từ; giữ nội dung từ/nghĩa đã có và bổ sung liên kết chủ đề. Không tự điền từ vào bộ sưu tập cá nhân. Có thể dùng Admin để thêm từ riêng thay cho bộ khởi đầu này.

Nếu server cũ đang chạy, Ctrl+C ở terminal server rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Android Studio mở `frontend`, chạy app trên emulator. Trong terminal khác, nối API:

```powershell
& "D:\PhanMem\AndroidStudioSDK\platform-tools\adb.exe" reverse tcp:8000 tcp:8000
```

Đăng nhập → Trang chủ/Luyện tập → Trò chơi. Để thử bộ từ đã lưu, lưu vài từ trong Kho từ vựng trước. Để thử Từ khó, đánh giá Cần ôn lại bằng Flashcard, trả lời sai Quiz hoặc để từ chạm đáy trong một màn đã gửi kết quả.

### Dữ liệu đi qua những đâu?

```text
GamesFragment chọn nguồn từ
  → GameRepository + Retrofit gửi nguồn và UUID lượt chơi
  → /games/word-shooter xác thực tài khoản
  → game_service chọn và chụp lại bộ từ từ PostgreSQL
  → game_runs + game_rounds lưu lượt và bộ từ của màn
  → WordShooterEngine xử lý rơi, gõ chữ, combo trên Android
  → hết màn gửi các từ đúng/bỏ lỡ theo thứ tự hoàn thành
  → backend kiểm tra bộ từ, đáp án, số bỏ lỡ; tự tính combo và điểm
  → lưu kết quả game_rounds + learning_events(kind=GAME) + learning_progress
  → Android hiện kết quả, gọi API màn tiếp theo
```

| API có Bearer token | Chức năng |
|---|---|
| `POST /games/word-shooter` | Tạo hoặc phục hồi lượt theo `client_session_id`; nguồn RANDOM/TOPIC/SAVED/DIFFICULT/REVIEW |
| `GET /games/word-shooter/{run_id}` | Lấy lượt và màn hiện tại, chỉ chủ tài khoản được xem |
| `POST /games/word-shooter/{run_id}/rounds/{round_id}/finish` | Gửi kết quả một màn; server tính điểm/combo, ghi tiến độ |
| `POST /games/word-shooter/{run_id}/rounds/{round_id}/next` | Tạo màn tiếp hoặc chơi lại màn thua; gọi lại không nhảy nhiều màn |

Backend không nhận điểm hoặc combo tự khai từ Android. Kết quả gửi lại giống nhau không tạo thêm lượt học; gửi khác kết quả đã chốt trả 409. Từ chưa xử lý khi thua không bị tính là sai. Chơi đúng một từ không tự đổi trạng thái thành MASTERED; đánh giá Flashcard đã có được giữ. Mỗi từ được xử lý trong màn đã gửi tính một lượt học vào mục tiêu/streak theo giờ Việt Nam. Không cộng vào thống kê Quiz.

Trạng thái đang gõ và thời gian rơi lưu riêng theo tài khoản trên thiết bị, ghi lại định kỳ/khi thao tác/khi tạm dừng. Kết quả chỉ được xác nhận trên server khi kết thúc màn; nếu mất mạng, Android giữ yêu cầu để thử lại. Sau khi xóa dữ liệu app hoặc đổi thiết bị, không có phần chữ đang gõ; backend vẫn giữ màn và các kết quả đã gửi. Đây là trò luyện tập, chưa có cơ chế chống gian lận cho thi đấu.

### File chính và kiểm thử

- Backend: `app/models/game.py`, `schemas/game.py`, `routers/games.py`, `services/game_service.py`, migration `0006_word_shooter.py`.
- Android: `ui/GameScreens.kt`, `ui/WordShooterView.kt`, `game/WordShooterEngine.kt`, `data/repository/GameRepository.kt`.
- `tests/test_game_flow.py`: kiểm tra nguồn từ, phân quyền theo tài khoản, chấm điểm, retry đồng thời, combo, thua/chơi lại, chuyển màn không lặp từ đã đúng, kết thúc chặng và bảo toàn dữ liệu migration.
- `WordShooterEngineTest.kt`: luật gõ sai giữ chữ/combo, combo20, lần bỏ lỡ thứ 4, tạm dừng/phục hồi, đổi mục tiêu và dấu cách điền sẵn.

Chạy backend tests từ `backend` (database tạm, không thêm fixture vào database ứng dụng):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Chạy Kotlin unit tests và build từ `frontend`, với Gradle JVM đúng như mục 3:

```powershell
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
```


Kiểm tra ngày 21/10/2026: **30 backend tests, 7 Kotlin unit tests và build APK đều thành công**. Kiểm thử trực tiếp trên emulator xác nhận gõ sai giữ chữ/combo; hoàn thành 20 từ đạt combo20; ngắt mạng lúc gửi rồi thử lại chỉ ghi kết quả một lần; màn tiếp không lặp từ đã đúng; tạm dừng, đóng/mở và xoay màn hình giữ trạng thái; lần chạm đáy thứ 4 thua và chơi lại đúng màn; chọn chủ đề/từ đã lưu/từ khó lấy đúng dữ liệu. Đã khôi phục SharedPreferences và hướng màn hình ban đầu, xóa tài khoản/dữ liệu kiểm thử. Trên máy phát triển đã chạy migration 0006 và seed thêm 93 từ còn thiếu, không sửa nội dung từ cũ.
