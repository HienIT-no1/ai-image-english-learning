package com.example.englishlearningapp.ui

import android.content.ActivityNotFoundException
import android.net.Uri
import android.os.Bundle
import android.widget.LinearLayout
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import com.example.englishlearningapp.R
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class CameraFragment : ScreenFragment() {
    private var image: String? = null
    private var pendingCamera: String? = null
    private var failed = false
    private val gallery = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if(uri!=null) {
            try { requireContext().contentResolver.takePersistableUriPermission(uri,android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) } catch (_: SecurityException) { }
            image=uri.toString(); failed=false
            if(view!=null) refresh()
        }
    }
    private val camera = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if(success) { image=pendingCamera; failed=false }
        if(view!=null) refresh()
    }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state); image=state?.getString("image"); pendingCamera=state?.getString("pendingCamera"); failed=state?.getBoolean("failed") ?: false
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state); state.putString("image",image); state.putString("pendingCamera",pendingCamera); state.putBoolean("failed",failed)
    }
    override fun render() {
        header("SEE IT. LEARN IT.", "Khám phá bằng ảnh", "Một vật quen thuộc. Một từ mới. Một bước tiến.")
        val preview=column(color=Palette.elevated,padding=22)
        if(image!=null) {
            val photo=ImagePreviewView(requireContext(),Uri.parse(image))
            preview.addView(photo,LinearLayout.LayoutParams(-1,dp(220)))
        } else {
            text("⌜                 ⌝",28,Palette.blue,parent=preview,center=true)
            text("📷",76,parent=preview,center=true)
            text("⌞                 ⌟",28,Palette.blue,parent=preview,center=true)
            text("Đặt vật thể trong khung hình",16,bold=true,parent=preview,center=true)
            text("Ánh sáng tốt giúp ảnh rõ nét hơn",12,Palette.muted,parent=preview,center=true)
        }
        button("Chụp ảnh mới") {
            try {
                val dir=File(requireContext().cacheDir,"camera").apply { mkdirs() }
                val file=File.createTempFile("capture_",".jpg",dir)
                val uri=FileProvider.getUriForFile(requireContext(),"${requireContext().packageName}.files",file)
                pendingCamera=uri.toString()
                camera.launch(uri)
            } catch (_: ActivityNotFoundException) {
                toast("Thiết bị không có ứng dụng camera. Hãy chọn ảnh từ thư viện.")
            } catch (_: java.io.IOException) {
                toast("Không tạo được file ảnh. Hãy kiểm tra dung lượng còn trống.")
            } catch (_: SecurityException) {
                toast("Không mở được camera. Hãy chọn ảnh từ thư viện.")
            }
        }
        button("Chọn ảnh từ thư viện",outlined=true) {
            try { gallery.launch(arrayOf("image/*")) }
            catch (_: ActivityNotFoundException) { toast("Không tìm thấy ứng dụng chọn ảnh trên thiết bị.") }
            catch (_: SecurityException) { toast("Không mở được thư viện ảnh trên thiết bị.") }
        }
        val explanation=column(color=Palette.surface)
        text("✦  Trải nghiệm nhận diện",16,Palette.purple,true,explanation)
        text("Chưa kết nối AI. Ảnh của bạn chỉ dùng để xem trước; kết quả Apple, Book và Coffee là dữ liệu mẫu cố định.",13,Palette.muted,parent=explanation)
        if(failed) notice("Không đọc được ảnh đã chọn. Hãy chọn lại ảnh khác.")
        button(if(image==null) "Thử với ảnh minh họa" else "Xem kết quả nhận diện mẫu",Palette.purple) {
            val timestamp=SimpleDateFormat("dd/MM/yyyy HH:mm",Locale.getDefault()).format(Date())
            store.history=(store.history+"apple|$timestamp").takeLast(50)
            go(R.id.recognitionFragment,"image" to image)
        }
        tile("◷","Lịch sử khám phá","Xem lại những phiên dùng thử") { go(R.id.historyFragment) }
    }
}

class RecognitionFragment : ScreenFragment() {
    override fun render() {
        header("ẢNH → TỪ VỰNG", "Khám phá mới của bạn", "Chọn một từ để xem nghĩa, ví dụ và nghe phát âm.",true)
        val preview=column(color=Palette.elevated)
        val uri=arguments?.getString("image")
        if(uri!=null) {
            val photo=ImagePreviewView(requireContext(),Uri.parse(uri))
            preview.addView(photo,LinearLayout.LayoutParams(-1,dp(180)))
        } else text("🍎   📚   ☕",56,parent=preview,center=true)
        text("✦  Kết quả minh họa",14,Palette.purple,true,preview)
        text("Đây là 3 từ mẫu, không phải đối tượng được AI xác định từ ảnh.",13,Palette.muted,parent=preview)
        section("3 từ để khám phá")
        listOf("apple","book","coffee").mapNotNull { words.find(it) }.forEach { wordRow(it) }
        button("Lưu cả 3 từ") {
            toast("Nhận diện mẫu chưa nối với kho từ trên máy chủ. Hãy lưu từ trong mục Từ vựng.")
        }
        button("Ôn luyện từ đã lưu",Palette.purple,outlined=true) { go(R.id.flashcardFragment) }
    }
}
