package com.example.englishlearningapp.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.media.ExifInterface
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import com.example.englishlearningapp.data.model.DetectionItemDto
import java.util.concurrent.Executors
import java.util.concurrent.Future

/** Decode a bounded thumbnail off the UI thread and render AI bounding boxes. */
class ImagePreviewView(context: Context, private val uri: Uri) : FrameLayout(context) {
    private val photo = ImageView(context).apply {
        scaleType = ImageView.ScaleType.FIT_CENTER
        contentDescription = "Ảnh nhận diện từ vựng"
    }
    private val status = TextView(context).apply {
        gravity = Gravity.CENTER
        setTextColor(Palette.muted)
        textSize = 14f
        setPadding(context.dp(16), context.dp(16), context.dp(16), context.dp(16))
    }

    private var task: Future<*>? = null
    private var generation = 0

    // Bounding box data
    private var detections: List<DetectionItemDto>? = null
    private var origWidth: Int = 0
    private var origHeight: Int = 0

    // Paints for overlay
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
        textSize = context.resources.displayMetrics.scaledDensity * 12f
        typeface = Typeface.DEFAULT_BOLD
    }
    private val textBounds = Rect()

    private val boxColors = intArrayOf(
        0xFF4F46E5.toInt(), // Indigo
        0xFF10B981.toInt(), // Emerald
        0xFFF59E0B.toInt(), // Amber
        0xFF06B6D4.toInt(), // Cyan
        0xFFEC4899.toInt(), // Pink
        0xFF8B5CF6.toInt()  // Violet
    )

    init {
        setWillNotDraw(false)
        addView(photo, LayoutParams(-1, -1))
        addView(status, LayoutParams(-1, -1))

        // Check if bitmap is already in memory cache for instant render
        val cached = bitmapCache[uri.toString()]
        if (cached != null && !cached.isRecycled) {
            photo.setImageBitmap(cached)
            status.visibility = GONE
        }
    }

    fun setDetections(items: List<DetectionItemDto>?, imageWidth: Int = 0, imageHeight: Int = 0) {
        this.detections = items
        this.origWidth = imageWidth
        this.origHeight = imageHeight
        postInvalidate()
    }

    override fun dispatchDraw(canvas: Canvas) {
        super.dispatchDraw(canvas)
        drawBoundingBoxes(canvas)
    }

    private fun getDrawableBounds(): RectF? {
        val d = photo.drawable ?: return null
        val viewW = photo.width.toFloat()
        val viewH = photo.height.toFloat()
        val dW = d.intrinsicWidth.toFloat()
        val dH = d.intrinsicHeight.toFloat()
        if (viewW <= 0f || viewH <= 0f || dW <= 0f || dH <= 0f) return null

        val scale = minOf(viewW / dW, viewH / dH)
        val actualW = dW * scale
        val actualH = dH * scale
        val left = (viewW - actualW) / 2f
        val top = (viewH - actualH) / 2f
        return RectF(left, top, left + actualW, top + actualH)
    }

    private fun drawBoundingBoxes(canvas: Canvas) {
        val items = detections ?: return
        if (items.isEmpty()) return
        val bounds = getDrawableBounds() ?: return

        val density = context.resources.displayMetrics.density
        val origW = if (origWidth > 0) origWidth.toFloat() else bounds.width()
        val origH = if (origHeight > 0) origHeight.toFloat() else bounds.height()

        for (i in items.indices) {
            val det = items[i]
            val b = det.box
            val color = boxColors[i % boxColors.size]

            // Support both pixel coordinates and normalized coordinates
            val normX1 = if (b.x1 <= 1.0f && b.x2 <= 1.0f && origW > 1f) b.x1 else (b.x1 / origW).coerceIn(0f, 1f)
            val normY1 = if (b.y1 <= 1.0f && b.y2 <= 1.0f && origH > 1f) b.y1 else (b.y1 / origH).coerceIn(0f, 1f)
            val normX2 = if (b.x1 <= 1.0f && b.x2 <= 1.0f && origW > 1f) b.x2 else (b.x2 / origW).coerceIn(0f, 1f)
            val normY2 = if (b.y1 <= 1.0f && b.y2 <= 1.0f && origH > 1f) b.y2 else (b.y2 / origH).coerceIn(0f, 1f)

            val left = bounds.left + normX1 * bounds.width()
            val top = bounds.top + normY1 * bounds.height()
            val right = bounds.left + normX2 * bounds.width()
            val bottom = bounds.top + normY2 * bounds.height()

            if (right <= left || bottom <= top) continue

            val boxRect = RectF(left, top, right, bottom)
            val cornerRadius = 6f * density

            // Draw subtle fill (12% opacity)
            fillPaint.color = (color and 0x00FFFFFF) or 0x1F000000
            canvas.drawRoundRect(boxRect, cornerRadius, cornerRadius, fillPaint)

            // Draw stroke
            boxPaint.color = color
            canvas.drawRoundRect(boxRect, cornerRadius, cornerRadius, boxPaint)

            // Draw label pill tag
            val word = det.vocabulary.word.ifBlank { det.label }
            val conf = (det.confidence * 100).toInt()
            val labelText = "$word $conf%"

            textPaint.getTextBounds(labelText, 0, labelText.length, textBounds)
            val textWidth = textPaint.measureText(labelText)
            val textHeight = textBounds.height().toFloat()

            val padH = 6f * density
            val padV = 3f * density
            val tagHeight = textHeight + padV * 2f
            val tagWidth = textWidth + padH * 2f

            var tagLeft = left
            var tagTop = top - tagHeight - 2f * density
            if (tagTop < bounds.top) {
                tagTop = top + 2f * density
            }
            val tagRight = tagLeft + tagWidth
            val tagBottom = tagTop + tagHeight

            val tagRect = RectF(tagLeft, tagTop, tagRight, tagBottom)
            tagBgPaint.color = color
            canvas.drawRoundRect(tagRect, 4f * density, 4f * density, tagBgPaint)

            val textBaseline = tagTop + padV + textHeight - textBounds.bottom
            canvas.drawText(labelText, tagLeft + padH, textBaseline, textPaint)
        }
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        val uriKey = uri.toString()
        val cached = bitmapCache[uriKey]
        if (cached != null && !cached.isRecycled) {
            photo.setImageBitmap(cached)
            status.visibility = GONE
            postInvalidate()
            return
        }

        val request = ++generation
        status.text = "Đang tải ảnh…"
        status.visibility = VISIBLE
        val resolver = context.applicationContext.contentResolver
        task = executor.submit {
            val bitmap = runCatching {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
                require(bounds.outWidth > 0 && bounds.outHeight > 0)
                var sample = 1
                while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 1024) sample *= 2
                val options = BitmapFactory.Options().apply { inSampleSize = sample }
                val decoded = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
                    ?: error("Cannot decode image")
                val orientation = runCatching {
                    resolver.openInputStream(uri)?.use {
                        ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
                    }
                }.getOrNull()
                val matrix = Matrix()
                when (orientation) {
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f, 1f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f, -1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> { matrix.setRotate(90f); matrix.postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
                    ExifInterface.ORIENTATION_TRANSVERSE -> { matrix.setRotate(-90f); matrix.postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(-90f)
                }
                if (matrix.isIdentity) decoded else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true).also {
                    if (it !== decoded) decoded.recycle()
                }
            }.getOrNull()

            mainHandler.post {
                if (request != generation || !isAttachedToWindow) {
                    bitmap?.recycle()
                } else if (bitmap == null) {
                    status.text = "Không đọc được ảnh. Hãy chọn ảnh khác."
                } else {
                    bitmapCache[uriKey] = bitmap
                    photo.setImageBitmap(bitmap)
                    status.visibility = GONE
                    postInvalidate()
                }
            }
        }
    }

    override fun onDetachedFromWindow() {
        generation++
        task?.cancel(true)
        task = null
        super.onDetachedFromWindow()
    }

    companion object {
        private val executor = Executors.newSingleThreadExecutor()
        private val mainHandler = Handler(Looper.getMainLooper())
        private val bitmapCache = object : LinkedHashMap<String, Bitmap>(8, 0.75f, true) {
            override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Bitmap>?): Boolean {
                if (size > 6) {
                    eldest?.value?.recycle()
                    return true
                }
                return false
            }
        }
    }
}
