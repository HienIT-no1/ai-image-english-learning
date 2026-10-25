package com.example.englishlearningapp.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.widget.LinearLayout
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.core.net.toUri
import androidx.lifecycle.lifecycleScope
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.CaptureDetectResponseDto
import com.example.englishlearningapp.data.model.DetectionItemDto
import com.example.englishlearningapp.data.model.Word
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class CameraFragment : ScreenFragment() {
    private var image: String? = null
    private var hasCameraPermission = false

    // Steady detection tracking
    private var steadyWord: String? = null
    private var steadyStartTime: Long = 0L
    private var lastShownWord: String? = null
    private var wordCardContainer: LinearLayout? = null
    private var realtimeCamView: CameraRealtimeView? = null

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        hasCameraPermission = granted
        if (view != null) refresh()
    }

    private val gallery = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            try {
                requireContext().contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) { }
            image = uri.toString()
            if (view != null) refresh()
        }
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        image = state?.getString("image")
        hasCameraPermission = ContextCompat.checkSelfPermission(
            requireContext(),
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state)
        state.putString("image", image)
    }

    override fun render() {
        header("TỪ VỰNG", "Khám phá vật thể")

        if (image != null) {
            val preview = column(color = Palette.elevated, padding = 16)
            val photo = ImagePreviewView(requireContext(), image!!.toUri())
            preview.addView(photo, LinearLayout.LayoutParams(-1, dp(240)))

            button("✨ Phân tích ảnh này", Palette.purple) {
                go(R.id.recognitionFragment, "image" to image)
            }
            button("Mở lại Camera", outlined = true) {
                image = null
                refresh()
            }
            return
        }

        if (!hasCameraPermission) {
            val preview = column(color = Palette.elevated, padding = 20)
            text("📷", 64, parent = preview, center = true)
            text("Quét từ vựng qua Camera", 16, bold = true, parent = preview, center = true)
            text("Bật quyền camera để quét đồ vật trực tiếp", 13, Palette.muted, parent = preview, center = true)

            button("Mở Camera", Palette.purple) {
                permissionLauncher.launch(Manifest.permission.CAMERA)
            }
            button("🖼️ Chọn ảnh từ thư viện", outlined = true) {
                try { gallery.launch(arrayOf("image/*")) } catch (_: Exception) { toast("Không mở được thư viện ảnh.") }
            }
            return
        }

        // Live CameraX view
        val camContainer = column(color = Palette.elevated, padding = 4)
        val realtimeCam = CameraRealtimeView(
            context = requireContext(),
            lifecycleOwner = viewLifecycleOwner,
            aiRepository = ai
        ) { detections ->
            handleDetections(detections)
        }
        realtimeCamView = realtimeCam
        camContainer.addView(realtimeCam, LinearLayout.LayoutParams(-1, dp(320)))

        // 3. Nút chụp ảnh để lưu vào CSDL
        button("📸 Chụp & Lưu vào CSDL", Palette.purple) {
            captureAndSave(realtimeCam)
        }

        // Nút chọn ảnh từ thư viện
        button("🖼️ Chọn ảnh từ thư viện", outlined = true) {
            try { gallery.launch(arrayOf("image/*")) } catch (_: Exception) { toast("Không mở được thư viện ảnh.") }
        }

        // 1. Vùng hiển thị từ vựng sau khi để im tầm 3 - 5s (NẰM DƯỚI nút "Chọn ảnh từ thư viện")
        wordCardContainer = column(parent = content, padding = 0)

        tile("◷", "Lịch sử nhận diện", "Xem lại các từ đã phát hiện") { go(R.id.historyFragment) }
    }

    private fun handleDetections(detections: List<DetectionItemDto>) {
        if (detections.isEmpty()) return
        val topDet = detections.maxByOrNull { it.confidence } ?: detections.first()
        val word = topDet.vocabulary.word.ifBlank { topDet.label }
        val now = System.currentTimeMillis()

        if (word.equals(steadyWord, ignoreCase = true)) {
            // Giữ im tầm 3s đến 5s thì tự động hiển thị thẻ từ vựng bên dưới
            if (now - steadyStartTime >= 3000L && word != lastShownWord) {
                lastShownWord = word
                wordCardContainer?.let { container ->
                    renderSteadyWordCard(topDet, container)
                }
                val timestamp = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()).format(Date())
                store.history = (store.history + "$word|$timestamp").takeLast(50)
            }
        } else {
            steadyWord = word
            steadyStartTime = now
        }
    }

    private fun renderSteadyWordCard(det: DetectionItemDto, container: LinearLayout) {
        container.removeAllViews()
        val card = column(color = Palette.surface, padding = 14, parent = container)

        text(det.vocabulary.word, 19, Palette.white, bold = true, parent = card)
        val ipa = det.vocabulary.ipa?.let { "$it • " }.orEmpty()
        val meaning = det.vocabulary.meaningVi ?: det.label
        text("$ipa$meaning", 13, Palette.muted, parent = card)

        val conf = (det.confidence * 100).toInt()
        text("Độ chính xác: $conf%", 11, Palette.blue, parent = card)

        button("🔊 Nghe phát âm", Palette.blue, parent = card) {
            speak(det.vocabulary.word)
        }

        val vocabId = det.vocabulary.vocabularyId?.toString()
        val matched = (vocabId?.let { words.find(it) } ?: words.findByEnglish(det.vocabulary.word))
            ?: if (vocabId != null) Word(
                id = vocabId,
                english = det.vocabulary.word,
                ipa = det.vocabulary.ipa.orEmpty(),
                meaning = det.vocabulary.meaningVi ?: det.label,
                example = "",
                translation = "",
                topic = "objects",
                symbol = "📦"
            ) else null

        if (matched != null) {
            val saved = matched.id in store.saved
            button(if (saved) "✓ Đã lưu trong từ vựng" else "＋ Lưu vào bộ sưu tập", outlined = saved, parent = card) {
                toggleSaved(matched)
                renderSteadyWordCard(det, container)
            }
        }
    }

    private fun captureAndSave(cam: CameraRealtimeView) {
        val bmp = cam.getCurrentBitmap()
        if (bmp == null) {
            toast("Camera chưa sẵn sàng, hãy thử lại.")
            return
        }
        try {
            val dir = File(requireContext().cacheDir, "camera").apply { mkdirs() }
            val file = File.createTempFile("capture_", ".jpg", dir)
            file.outputStream().use { out ->
                bmp.compress(Bitmap.CompressFormat.JPEG, 92, out)
            }
            val uri = FileProvider.getUriForFile(
                requireContext(),
                "${requireContext().packageName}.files",
                file
            )
            go(R.id.recognitionFragment, "image" to uri.toString())
        } catch (_: Exception) {
            toast("Không thể lưu ảnh chụp.")
        }
    }
}

class RecognitionFragment : ScreenFragment() {
    private var loading = false
    private var result: CaptureDetectResponseDto? = null
    private var errorMsg: String? = null
    private var analyzedUri: String? = null

    override fun render() {
        header("KẾT QUẢ", "Đối tượng nhận diện", "", true)

        val uriString = arguments?.getString("image")
        val preview = column(color = Palette.elevated, padding = 12)

        val photo = if (uriString != null) {
            ImagePreviewView(requireContext(), uriString.toUri()).also { p ->
                preview.addView(p, LinearLayout.LayoutParams(-1, dp(260)))
            }
        } else {
            text("📷", 56, parent = preview, center = true)
            null
        }

        // Tự động gọi API nhận diện khi mở màn hình
        if (uriString != null && result == null && !loading && analyzedUri != uriString) {
            analyzedUri = uriString
            loading = true
            lifecycleScope.launch {
                val res = ai.detectCapture(requireContext(), uriString.toUri())
                loading = false
                res.onSuccess {
                    result = it
                    errorMsg = null
                    if (it.detections.isNotEmpty()) {
                        val timestamp = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()).format(Date())
                        val firstWord = it.detections.first().vocabulary.word
                        store.history = (store.history + "$firstWord|$timestamp").takeLast(50)
                    }
                }.onFailure { err ->
                    errorMsg = err.message ?: "Lỗi kết nối máy chủ AI"
                }
                if (view != null) refresh()
            }
        }

        if (loading) {
            text("⚡ Đang nhận diện đối tượng...", 14, Palette.purple, true, preview)
            progress(50, 100, preview, Palette.purple)
            return
        }

        if (errorMsg != null) {
            val errBox = column(color = Palette.surface)
            text("❌ Không thể nhận diện", 16, Palette.red, true, errBox)
            text(errorMsg.orEmpty(), 13, Palette.muted, parent = errBox)
            button("Thử lại", Palette.purple) {
                result = null
                errorMsg = null
                analyzedUri = null
                refresh()
            }
            return
        }

        val currentResult = result
        if (currentResult != null) {
            photo?.setDetections(currentResult.detections, currentResult.imageWidth, currentResult.imageHeight)

            if (currentResult.detections.isEmpty()) {
                notice("Không tìm thấy đồ vật nào. Hãy thử chụp gần hơn.")
            } else {
                section("Từ vựng phát hiện (${currentResult.detections.size}):")
                currentResult.detections.forEach { det ->
                    val card = column(color = Palette.surface, padding = 14)

                    text(det.vocabulary.word, 18, Palette.white, bold = true, parent = card)
                    val ipaText = det.vocabulary.ipa?.let { "$it • " }.orEmpty()
                    val meaningText = det.vocabulary.meaningVi ?: det.label
                    text("$ipaText$meaningText", 13, Palette.muted, parent = card)

                    val confPercent = (det.confidence * 100).toInt()
                    text("Độ chính xác: $confPercent%", 11, Palette.blue, parent = card)

                    button("🔊 Nghe", Palette.blue, parent = card) {
                        speak(det.vocabulary.word)
                    }

                    val vocabId = det.vocabulary.vocabularyId?.toString()
                    val matchedWord = (vocabId?.let { words.find(it) } ?: words.findByEnglish(det.vocabulary.word))
                        ?: if (vocabId != null) Word(
                            id = vocabId,
                            english = det.vocabulary.word,
                            ipa = det.vocabulary.ipa.orEmpty(),
                            meaning = det.vocabulary.meaningVi ?: det.label,
                            example = "",
                            translation = "",
                            topic = "objects",
                            symbol = "📦"
                        ) else null

                    if (matchedWord != null) {
                        val saved = matchedWord.id in store.saved
                        button(if (saved) "✓ Đã lưu" else "＋ Lưu vào bộ sưu tập", outlined = saved, parent = card) {
                            toggleSaved(matchedWord)
                            refresh()
                        }
                    }
                }
            }
        }

        button("Chụp ảnh khác", outlined = true) {
            go(R.id.cameraFragment)
        }
        button("Ôn luyện từ vựng", Palette.purple) {
            go(R.id.flashcardFragment)
        }
    }
}
