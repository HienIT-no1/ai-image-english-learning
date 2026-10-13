package com.example.englishlearningapp.data.remote

import kotlinx.coroutines.CancellationException
import org.json.JSONArray
import org.json.JSONObject
import retrofit2.Response
import java.io.IOException

class ApiException(val status: Int, message: String) : Exception(message)
fun <T> Response<T>.requireData(): T {
    if (!isSuccessful) {
        val detail = runCatching {
            val d = JSONObject(errorBody()?.string().orEmpty()).get("detail")
            if (d is JSONArray) d.getJSONObject(0).optString("msg") else d.toString()
        }.getOrNull()
        val message = when (detail) {
            "Username already exists" -> "Tên đăng nhập đã tồn tại"
            "Email already exists" -> "Email đã được sử dụng"
            "Invalid username or password" -> "Sai tên đăng nhập hoặc mật khẩu"
            "Admin access required" -> "Tài khoản không còn quyền quản trị."
            "Topic not found" -> "Chủ đề không còn tồn tại. Hãy tải lại danh sách."
            "Topic still contains vocabulary" -> "Chủ đề còn có từ vựng. Hãy chuyển từ sang chủ đề khác trước khi xóa."
            "Data conflict; name or slug already exists" -> "Từ hoặc mã chủ đề đã tồn tại. Hãy tải lại danh sách."
            "Existing example cannot be cleared in this editor" -> "Hãy giữ hoặc sửa câu ví dụ hiện có."
            "Vocabulary not found" -> "Từ vựng không còn tồn tại"
            else -> if (code()==401) "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại." else "Máy chủ trả lỗi ${code()}. Hãy thử lại."
        }
        throw ApiException(code(),message)
    }
    return body() ?: throw Exception("Máy chủ chưa trả dữ liệu hợp lệ.")
}
suspend fun <T> apiResult(block: suspend () -> T): Result<T> = try { Result.success(block()) }
catch (e: CancellationException) { throw e }
catch (e: IOException) { Result.failure(Exception("Không kết nối được máy chủ. Kiểm tra kết nối rồi thử lại.")) }
catch (e: Exception) { Result.failure(e) }
