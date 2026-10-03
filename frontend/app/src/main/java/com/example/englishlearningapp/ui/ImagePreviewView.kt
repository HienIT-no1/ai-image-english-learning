package com.example.englishlearningapp.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import java.util.concurrent.Executors
import java.util.concurrent.Future

/** Decode a bounded thumbnail off the UI thread; the original file remains unchanged. */
class ImagePreviewView(context: Context, private val uri: Uri) : FrameLayout(context) {
    private val photo=ImageView(context).apply {
        scaleType=ImageView.ScaleType.FIT_CENTER
        contentDescription="Ảnh đã chọn để học từ vựng"
    }
    private val status=TextView(context).apply {
        gravity=Gravity.CENTER; setTextColor(Palette.muted); textSize=14f
        setPadding(context.dp(16),context.dp(16),context.dp(16),context.dp(16))
    }
    private var task: Future<*>?=null
    private var generation=0
    init {
        addView(photo,LayoutParams(-1,-1))
        addView(status,LayoutParams(-1,-1))
    }
    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        val request=++generation
        status.text="Đang tải ảnh…"; status.visibility=VISIBLE
        val resolver=context.applicationContext.contentResolver
        task=executor.submit {
            val bitmap=runCatching {
                val bounds=BitmapFactory.Options().apply { inJustDecodeBounds=true }
                resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it,null,bounds) }
                require(bounds.outWidth>0 && bounds.outHeight>0)
                var sample=1
                while (maxOf(bounds.outWidth,bounds.outHeight)/sample>1024) sample*=2
                val options=BitmapFactory.Options().apply { inSampleSize=sample }
                val decoded=resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it,null,options) }
                    ?: error("Cannot decode image")
                val orientation=runCatching {
                    resolver.openInputStream(uri)?.use { ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION,ExifInterface.ORIENTATION_NORMAL) }
                }.getOrNull()
                val matrix=Matrix()
                when (orientation) {
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f,1f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f,-1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> { matrix.setRotate(90f); matrix.postScale(-1f,1f) }
                    ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
                    ExifInterface.ORIENTATION_TRANSVERSE -> { matrix.setRotate(-90f); matrix.postScale(-1f,1f) }
                    ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(-90f)
                }
                if (matrix.isIdentity) decoded else Bitmap.createBitmap(decoded,0,0,decoded.width,decoded.height,matrix,true).also {
                    if (it !== decoded) decoded.recycle()
                }
            }.getOrNull()
            mainHandler.post {
                if (request!=generation || !isAttachedToWindow) {
                    bitmap?.recycle()
                } else if (bitmap==null) {
                    status.text="Không đọc được ảnh. Hãy chọn lại ảnh từ thư viện hoặc chụp ảnh mới."
                } else {
                    photo.setImageBitmap(bitmap); status.visibility=GONE
                }
            }
        }
    }
    override fun onDetachedFromWindow() {
        generation++; task?.cancel(true); task=null
        photo.setImageDrawable(null)
        super.onDetachedFromWindow()
    }
    companion object {
        private val executor=Executors.newSingleThreadExecutor()
        private val mainHandler=Handler(Looper.getMainLooper())
    }
}
