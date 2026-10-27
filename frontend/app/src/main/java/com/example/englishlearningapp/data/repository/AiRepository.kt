package com.example.englishlearningapp.data.repository

import android.content.Context
import android.net.Uri
import com.example.englishlearningapp.data.model.CaptureDetectResponseDto
import com.example.englishlearningapp.data.remote.ApiService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class AiRepository(private val api: ApiService) {

    suspend fun detectCapture(context: Context, imageUri: Uri, conf: Float = 0.35f): Result<CaptureDetectResponseDto> = withContext(Dispatchers.IO) {
        try { Result.success(run {
            val contentResolver = context.contentResolver
            val bytes = contentResolver.openInputStream(imageUri)?.use { it.readBytes() }
                ?: error("Không thể đọc file ảnh từ bộ nhớ.")

            val requestFile = bytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", "camera_capture.jpg", requestFile)

            val response = api.detectCapture(body, conf)
            if (!response.isSuccessful) {
                error("Lỗi nhận diện AI (HTTP ${response.code()}): ${response.errorBody()?.string() ?: "Thử lại sau"}")
            }
            response.body() ?: error("Không nhận được kết quả từ máy chủ.")
        }) } catch (cancelled: CancellationException) { throw cancelled }
        catch (error: Exception) { Result.failure(error) }
    }

    suspend fun detectRealtime(imageBytes: ByteArray, conf: Float = 0.35f): Result<com.example.englishlearningapp.data.model.RealtimeDetectResponseDto> = withContext(Dispatchers.IO) {
        try { Result.success(run {
            val requestFile = imageBytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", "frame.jpg", requestFile)

            val response = api.detectRealtime(body, conf)
            if (!response.isSuccessful) {
                error("Lỗi nhận diện realtime (HTTP ${response.code()})")
            }
            response.body() ?: error("Không có dữ liệu phản hồi.")
        }) } catch (cancelled: CancellationException) { throw cancelled }
        catch (error: Exception) { Result.failure(error) }
    }
}
