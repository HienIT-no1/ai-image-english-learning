package com.example.englishlearningapp.ui

import android.content.Context
import android.graphics.*
import android.os.SystemClock
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import com.example.englishlearningapp.game.*
import kotlin.math.*

/** Native canvas animates only while visible; the rules live in WordShooterEngine. */
class WordShooterView(context: Context,val engine: WordShooterEngine) : View(context) {
    var onChanged: (() -> Unit)?=null
    var onFinished: (() -> Unit)?=null
    var onSpoken: ((String) -> Unit)?=null
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    private val density=resources.displayMetrics.density
    private fun d(value: Float)=value*density
    private var previousFrame=0L
    private var clock=0f
    private var lastSaved=0f
    private var finishSent=false
    private var flashUntil=0L
    private var flashIndex: Int?=null
    private var message=""
    private var messageUntil=0L
    private val boxes=mutableMapOf<Int,RectF>()
    private data class Bullet(val letter: Char,val start: Long,val x: Float,val y: Float,val good: Boolean,val combo: Int)
    private val bullets=mutableListOf<Bullet>()
    private data class Burst(val x: Float,val y: Float,val start: Long,val combo: Int)
    private val bursts=mutableListOf<Burst>()
    init {
        isFocusable=true;isFocusableInTouchMode=true
        contentDescription="Vùng chơi bắn chữ. Chạm một từ để ngắm."
        setOnKeyListener { _,keyCode,event ->
            if(event.action==KeyEvent.ACTION_DOWN && keyCode in KeyEvent.KEYCODE_A..KeyEvent.KEYCODE_Z) {
                fire(('a'.code+keyCode-KeyEvent.KEYCODE_A).toChar());true
            } else false
        }
    }
    fun fire(letter: Char) {
        val target=engine.target ?: return
        val box=boxes[target.index]
        val english=engine.words[target.index].english
        val result=engine.shoot(letter)
        if(result==Shot.IGNORED) return
        val now=SystemClock.uptimeMillis()
        bullets.add(Bullet(letter.uppercaseChar(),now,box?.centerX() ?: width/2f,box?.centerY() ?: height/2f,result!=Shot.WRONG,engine.combo))
        if(result==Shot.WRONG) {
            flashIndex=target.index;flashUntil=now+280
            message="Chưa đúng chữ • Thử lại nhé";messageUntil=now+650
        }
        if(result==Shot.COMPLETE) {
            bursts.add(Burst(box?.centerX() ?: width/2f,box?.centerY() ?: height/2f,now,engine.combo))
            message=if(engine.combo>=5) "COMBO ${engine.combo}!" else "Đúng rồi!"
            messageUntil=now+1000;onSpoken?.invoke(english)
        }
        onChanged?.invoke();requestFocus();invalidate();checkFinished()
    }
    private fun checkFinished() {
        if(engine.ended && !finishSent) { finishSent=true;post { onFinished?.invoke() } }
    }
    override fun onAttachedToWindow() { super.onAttachedToWindow();previousFrame=0;invalidate() }
    override fun onDetachedFromWindow() { previousFrame=0;super.onDetachedFromWindow() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility);previousFrame=0 }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val now=SystemClock.uptimeMillis()
        val delta=if(previousFrame==0L) 0f else ((now-previousFrame)/1000f).coerceIn(0f,0.1f)
        previousFrame=now
        if(!engine.paused && !engine.ended) {
            val missed=engine.tick(delta);clock+=delta
            if(missed.isNotEmpty()) {
                val last=missed.last()
                val word=engine.words.first { it.id==last.id }
                message="${word.english} • ${word.meaning}";messageUntil=now+1800
                onSpoken?.invoke(word.english);onChanged?.invoke()
            }
            if(clock-lastSaved>=1f) { lastSaved=clock;onChanged?.invoke() }
        }
        val w=width.toFloat();val h=height.toFloat()
        paint.shader=LinearGradient(0f,0f,0f,h,intArrayOf(Palette.skyStart,Palette.skyEnd),null,Shader.TileMode.CLAMP)
        canvas.drawRoundRect(0f,0f,w,h,d(18f),d(18f),paint);paint.shader=null
        for(i in 0..33) {
            paint.color=if(Palette.light) Palette.line else if(i%3==0) 0xFF8178B5.toInt() else 0xFF485274.toInt()
            canvas.drawCircle(w*((i*37%97)/97f),h*((i*19%73)/100f),d(if(i%3==0) 1.4f else 0.8f),paint)
        }
        val bottom=h-d(60f)
        paint.color=Palette.red;paint.strokeWidth=d(2f)
        canvas.drawLine(d(10f),bottom,w-d(10f),bottom,paint)
        label(canvas,"VẠCH ĐÁY",w-d(12f),bottom+d(13f),9f,Palette.muted,Paint.Align.RIGHT)
        boxes.clear()
        engine.state.active.forEach { item ->
            val cardWidth=(w-d(30f))/2f
            val cardHeight=minOf(d(104f),maxOf(d(78f),h*0.30f))
            val x=d(10f)+item.lane*(cardWidth+d(10f))
            val y=d(10f)+item.progress*(bottom-cardHeight-d(10f))
            val shake=if(item.index==flashIndex && now<flashUntil) sin(now/18.0).toFloat()*d(3f) else 0f
            val rect=RectF(x+shake,y,x+cardWidth+shake,y+cardHeight)
            boxes[item.index]=rect
            val selected=engine.state.targetIndex==item.index
            paint.style=Paint.Style.FILL;paint.color=if(selected) Palette.elevated else Palette.surface
            canvas.drawRoundRect(rect,d(12f),d(12f),paint)
            paint.style=Paint.Style.STROKE;paint.strokeWidth=d(if(selected) 2f else 1f)
            paint.color=if(now<flashUntil && item.index==flashIndex) Palette.red else if(selected) Palette.blue else Palette.line
            canvas.drawRoundRect(rect,d(12f),d(12f),paint);paint.style=Paint.Style.FILL
            val word=engine.words[item.index]
            canvas.save();canvas.clipRect(rect)
            paragraph(canvas,word.meaning,rect.left+d(9f),rect.top+d(7f),rect.width()-d(18f),13f,Palette.white,2)
            val mask=engine.masked(item).let { if(it.length<=9) it.toCharArray().joinToString(" ") else it }
            paragraph(canvas,mask,rect.left+d(9f),rect.top+cardHeight*0.48f,rect.width()-d(18f),16f,if(selected) Palette.blue else Palette.muted,2,true)
            canvas.restore()
        }
        // Cannon glows with the current combo, while its muzzle follows the selected target.
        val combo=engine.combo
        val glow=when { combo>=15->Palette.orange;combo>=10->Palette.purple;combo>=5->Palette.green;else->Palette.blue }
        if(combo>=5) {
            paint.color=glow;paint.alpha=35
            canvas.drawCircle(w/2,h-d(22f),d(28f)+sin(now/180.0).toFloat()*d(3f),paint);paint.alpha=255
        }
        canvas.save();canvas.rotate(((engine.target?.lane ?: 0)*2-1)*12f,w/2,h-d(20f))
        paint.color=glow;canvas.drawRoundRect(w/2-d(7f),h-d(52f),w/2+d(7f),h-d(17f),d(5f),d(5f),paint)
        canvas.restore();paint.color=Palette.elevated
        canvas.drawRoundRect(w/2-d(25f),h-d(26f),w/2+d(25f),h-d(5f),d(10f),d(10f),paint)
        paint.color=glow;canvas.drawCircle(w/2,h-d(18f),d(8f),paint)
        bullets.removeAll { now-it.start>400 }
        bullets.forEach { bullet ->
            val t=((now-bullet.start)/400f).coerceIn(0f,1f)
            val x=w/2+(bullet.x-w/2)*t
            val y=h-d(45f)+(bullet.y-h+d(45f))*t
            paint.color=if(bullet.good) glow else Palette.red
            if(bullet.combo>=5 && bullet.good) {
                paint.alpha=80;canvas.drawLine(x,y,x-(bullet.x-w/2)*0.09f,y+d(24f),paint);paint.alpha=255
            }
            canvas.drawCircle(x,y,d(11f),paint)
            label(canvas,bullet.letter.toString(),x,y+d(5f),13f,Palette.onAccent,Paint.Align.CENTER)
        }
        bursts.removeAll { now-it.start>700 }
        bursts.forEach { burst ->
            val t=(now-burst.start)/700f
            paint.color=if(burst.combo>=5) glow else Palette.green;paint.alpha=((1-t)*255).toInt().coerceIn(0,255)
            for(i in 0..11) {
                val angle=i*PI/6
                canvas.drawCircle(burst.x+cos(angle).toFloat()*t*d(45f),burst.y+sin(angle).toFloat()*t*d(45f),d(3f)*(1-t),paint)
            }
            paint.alpha=255
        }
        if(now<messageUntil) label(canvas,message,w/2,d(24f),if(message.startsWith("COMBO")) 22f else 13f,if(message.startsWith("COMBO")) glow else Palette.orange,Paint.Align.CENTER)
        if(engine.paused && !engine.ended) {
            paint.color=Palette.gameOverlay;canvas.drawRoundRect(0f,0f,w,h,d(18f),d(18f),paint)
            label(canvas,"SẴN SÀNG BẮN CHỮ?",w/2,h/2-d(8f),18f,Palette.white,Paint.Align.CENTER)
            label(canvas,"Bấm Bắt đầu / Tiếp tục ở phía trên",w/2,h/2+d(20f),12f,Palette.muted,Paint.Align.CENTER)
        }
        checkFinished()
        if(isShown && (!engine.paused || bullets.isNotEmpty() || bursts.isNotEmpty() || now<messageUntil)) postInvalidateOnAnimation()
    }
    private fun label(canvas: Canvas,text: String,x: Float,y: Float,size: Float,color: Int,align: Paint.Align) {
        paint.color=color;paint.textSize=d(size);paint.typeface=Typeface.create("sans-serif",Typeface.BOLD);paint.textAlign=align
        canvas.drawText(text,x,y,paint);paint.textAlign=Paint.Align.LEFT
    }
    private fun paragraph(canvas: Canvas,text: String,x: Float,y: Float,width: Float,size: Float,color: Int,lines: Int,mono: Boolean=false) {
        val textPaint=TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            this.color=color;textSize=d(size);typeface=if(mono) Typeface.MONOSPACE else Typeface.DEFAULT
        }
        val layout=StaticLayout.Builder.obtain(text,0,text.length,textPaint,width.toInt().coerceAtLeast(1))
            .setAlignment(Layout.Alignment.ALIGN_CENTER).setMaxLines(lines)
            .setEllipsize(android.text.TextUtils.TruncateAt.END).setIncludePad(false).build()
        canvas.save();canvas.translate(x,y);layout.draw(canvas);canvas.restore()
    }
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if(event.action==MotionEvent.ACTION_UP) {
            boxes.entries.firstOrNull { it.value.contains(event.x,event.y) }?.let { engine.select(it.key);onChanged?.invoke();invalidate() }
            performClick();requestFocus()
        }
        return true
    }
    override fun performClick(): Boolean { super.performClick();return true }
}
