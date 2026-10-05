package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.LoginRequest
import com.example.englishlearningapp.data.model.RegisterRequest
import com.example.englishlearningapp.data.model.UserDto
import com.example.englishlearningapp.data.remote.ApiService
import org.json.JSONArray
import org.json.JSONObject
import retrofit2.Response
import java.io.IOException
import java.util.concurrent.CancellationException

class AuthRepository(
    private val api: ApiService,
    private val store: LearningStore
) {
    suspend fun login(username: String, password: String): Result<UserDto> = call {
        val res = api.login(LoginRequest(username, password))
        if (!res.isSuccessful) throw ApiException(message(res))
        store.token = res.body()!!.accessToken

        val me = api.me()
        if (!me.isSuccessful) throw ApiException(message(me))
        me.body()!!
    }

    suspend fun register(username: String, email: String, password: String): Result<UserDto> = call {
        val res = api.register(RegisterRequest(username, email, password))
        if (!res.isSuccessful) throw ApiException(message(res))
        // Đăng ký xong tự đăng nhập luôn
        login(username, password).getOrThrow()
    }

    fun logout() {
        store.token = null
        store.signedIn = false
    }

    private class ApiException(msg: String) : Exception(msg)

    private suspend fun <T> call(block: suspend () -> T): Result<T> = try {
        Result.success(block())
    } catch (e: CancellationException) {
        throw e
    } catch (e: IOException) {
    android.util.Log.e("AuthRepo", "Network error", e)
    Result.failure(Exception("Không kết nối được máy chủ (${e.javaClass.simpleName}: ${e.message})"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    private fun message(res: Response<*>): String {
        val raw = res.errorBody()?.string().orEmpty()
        val detail = runCatching {
            val d = JSONObject(raw).get("detail")
            if (d is JSONArray) d.getJSONObject(0).optString("msg") else d.toString()
        }.getOrNull()
        return when (detail) {
            "Username already exists" -> "Tên đăng nhập đã tồn tại"
            "Email already exists" -> "Email đã được sử dụng"
            "Invalid username or password" -> "Sai tên đăng nhập hoặc mật khẩu"
            "Could not validate credentials" -> "Phiên đăng nhập đã hết hạn"
            null, "" -> "Lỗi ${res.code()}"
            else -> detail
        }
    }
}