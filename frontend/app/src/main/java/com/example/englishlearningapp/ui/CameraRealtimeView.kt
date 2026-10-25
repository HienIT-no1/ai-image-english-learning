package com.example.englishlearningapp.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.util.AttributeSet
import android.view.View
import android.widget.FrameLayout
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.lifecycleScope
import com.example.englishlearningapp.data.model.DetectionItemDto
import com.example.englishlearningapp.data.repository.AiRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

/**
 * CameraX Live Preview with real-time Bounding Box overlay.
 */
class CameraRealtimeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : FrameLayout(context, attrs, defStyleAttr) {

    private var lifecycleOwner: LifecycleOwner? = null
    private var aiRepository: AiRepository? = null
    private var onDetections: ((List<DetectionItemDto>) -> Unit)? = null
    var onError: ((Throwable) -> Unit)? = null

    private val previewView = PreviewView(context).apply {
        scaleType = PreviewView.ScaleType.FILL_CENTER
    }
    private val overlayView = RealtimeOverlayView(context)

    private var loopJob: Job? = null
    private var isAnalyzing = false

    constructor(
        context: Context,
        lifecycleOwner: LifecycleOwner,
        aiRepository: AiRepository,
        onDetections: ((List<DetectionItemDto>) -> Unit)? = null
    ) : this(context) {
        this.lifecycleOwner = lifecycleOwner
        this.aiRepository = aiRepository
        this.onDetections = onDetections
    }

    init {
        addView(previewView, LayoutParams(-1, -1))
        addView(overlayView, LayoutParams(-1, -1))
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        val owner = lifecycleOwner ?: return
        startCamera(owner)
    }

    private fun startCamera(owner: LifecycleOwner) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(owner, cameraSelector, preview)
                startDetectionLoop(owner)
            } catch (_: Exception) { }
        }, ContextCompat.getMainExecutor(context))
    }

    private fun startDetectionLoop(owner: LifecycleOwner) {
        val repo = aiRepository ?: return
        loopJob?.cancel()
        loopJob = owner.lifecycleScope.launch {
            while (isActive) {
                delay(250) // Interval between detections (~4 FPS)
                if (isAnalyzing || !isAttachedToWindow) continue

                val bitmap = previewView.bitmap ?: continue
                isAnalyzing = true

                try {
                    val compressedBytes = withContext(Dispatchers.Default) {
                        val maxDim = maxOf(bitmap.width, bitmap.height)
                        val scale = if (maxDim > 640) 640f / maxDim else 1f
                        val scaledBitmap = if (scale < 1f) {
                            Bitmap.createScaledBitmap(
                                bitmap,
                                (bitmap.width * scale).toInt(),
                                (bitmap.height * scale).toInt(),
                                true
                            )
                        } else bitmap

                        val out = ByteArrayOutputStream()
                        scaledBitmap.compress(Bitmap.CompressFormat.JPEG, 75, out)
                        if (scaledBitmap !== bitmap) scaledBitmap.recycle()
                        out.toByteArray()
                    }

                    val result = repo.detectRealtime(compressedBytes)
                    result.onSuccess { res ->
                        overlayView.updateDetections(res.detections, res.imageWidth, res.imageHeight)
                        withContext(Dispatchers.Main) {
                            onDetections?.invoke(res.detections)
                        }
                    }.onFailure { err ->
                        withContext(Dispatchers.Main) {
                            onError?.invoke(err)
                        }
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        onError?.invoke(e)
                    }
                } finally {
                    isAnalyzing = false
                }
            }
        }
    }

    /** Returns current preview frame for full-resolution capture and saving. */
    fun getCurrentBitmap(): Bitmap? = previewView.bitmap

    override fun onDetachedFromWindow() {
        loopJob?.cancel()
        loopJob = null
        super.onDetachedFromWindow()
    }

    /**
     * Canvas view that renders bounding boxes over the camera stream.
     * Pre-allocates RectF and Paint objects to avoid GC churn in onDraw.
     */
    private class RealtimeOverlayView(context: Context) : View(context) {
        private var detections: List<DetectionItemDto> = emptyList()
        private var imgW: Int = 0
        private var imgH: Int = 0

        private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeWidth = context.resources.displayMetrics.density * 2.5f
        }
        private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.FILL
        }
        private val tagBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.FILL
        }
        private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textSize = context.resources.displayMetrics.density * 13f
            typeface = Typeface.DEFAULT_BOLD
        }
        private val textBounds = Rect()
        private val tempBoxRect = RectF()
        private val tempTagRect = RectF()

        private val colors = intArrayOf(
            0xFF4F46E5.toInt(), // Indigo
            0xFF10B981.toInt(), // Emerald
            0xFFF59E0B.toInt(), // Amber
            0xFF06B6D4.toInt(), // Cyan
            0xFFEC4899.toInt(), // Pink
            0xFF8B5CF6.toInt()  // Violet
        )

        fun updateDetections(items: List<DetectionItemDto>, width: Int, height: Int) {
            this.detections = items
            this.imgW = width
            this.imgH = height
            postInvalidate()
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            if (detections.isEmpty() || imgW <= 0 || imgH <= 0 || width <= 0 || height <= 0) return

            val density = resources.displayMetrics.density
            val viewW = width.toFloat()
            val viewH = height.toFloat()

            for (i in detections.indices) {
                val det = detections[i]
                val b = det.box
                val color = colors[i % colors.size]

                val normX1 = (b.x1 / imgW).coerceIn(0f, 1f)
                val normY1 = (b.y1 / imgH).coerceIn(0f, 1f)
                val normX2 = (b.x2 / imgW).coerceIn(0f, 1f)
                val normY2 = (b.y2 / imgH).coerceIn(0f, 1f)

                val left = normX1 * viewW
                val top = normY1 * viewH
                val right = normX2 * viewW
                val bottom = normY2 * viewH

                if (right <= left || bottom <= top) continue

                tempBoxRect.set(left, top, right, bottom)
                val cornerRadius = 6f * density

                // Subtle translucent fill
                fillPaint.color = (color and 0x00FFFFFF) or 0x22000000
                canvas.drawRoundRect(tempBoxRect, cornerRadius, cornerRadius, fillPaint)

                // Stroke outline
                boxPaint.color = color
                canvas.drawRoundRect(tempBoxRect, cornerRadius, cornerRadius, boxPaint)

                // Label pill tag
                val word = det.vocabulary.word.ifBlank { det.label }
                val conf = (det.confidence * 100).toInt()
                val labelText = "$word $conf%"

                textPaint.getTextBounds(labelText, 0, labelText.length, textBounds)
                val textW = textPaint.measureText(labelText)
                val textH = textBounds.height().toFloat()

                val padH = 6f * density
                val padV = 3f * density
                val tagH = textH + padV * 2f
                val tagW = textW + padH * 2f

                var tagLeft = left
                var tagTop = top - tagH - 2f * density
                if (tagTop < 0) tagTop = top + 2f * density
                val tagRight = tagLeft + tagW
                val tagBottom = tagTop + tagH

                tempTagRect.set(tagLeft, tagTop, tagRight, tagBottom)
                tagBgPaint.color = color
                canvas.drawRoundRect(tempTagRect, 4f * density, 4f * density, tagBgPaint)

                val textBaseline = tagTop + padV + textH - textBounds.bottom
                canvas.drawText(labelText, tagLeft + padH, textBaseline, textPaint)
            }
        }
    }
}
