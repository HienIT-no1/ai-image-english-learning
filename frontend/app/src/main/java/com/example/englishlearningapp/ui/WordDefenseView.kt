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

/** Original garden/monster artwork drawn locally; no asset downloads during play. */
class WordDefenseView(context: Context, val engine: WordDefenseEngine): View(context) {
    var onChanged: (() -> Unit)?=null
    var onFinished: (() -> Unit)?=null
    var onSpoken: ((String) -> Unit)?=null
    private val p=Paint(Paint.ANTI_ALIAS_FLAG)
    private val boxes=mutableMapOf<Int,RectF>()
    private var previous=0L
    private var savedAt=0L
    private var sent=false
    private var wrongIndex: Int?=null
    private var wrongUntil=0L
    private var message=""
    private var messageUntil=0L
    private data class Bullet(val letter: Char,val from: PointF,val to: PointF,val start: Long,val good: Boolean)
    private data class Burst(val center: PointF,val start: Long,val combo: Int)
    private val bullets=mutableListOf<Bullet>()
    private val bursts=mutableListOf<Burst>()
    private fun d(v: Float)=v*resources.displayMetrics.density
    private fun laneY(lane: Int)=d(30f)+(height-d(48f))/WordDefenseEngine.LANE_COUNT*(lane+.5f)
    init {
        isFocusable=true;isFocusableInTouchMode=true
        setOnKeyListener { _,code,event ->
            if(event.action==KeyEvent.ACTION_DOWN && code in KeyEvent.KEYCODE_A..KeyEvent.KEYCODE_Z) {
                fire(('a'.code+code-KeyEvent.KEYCODE_A).toChar());true
            } else false
        }
    }
    fun fire(letter: Char) {
        val target=engine.target ?: return
        val box=boxes[target.index]
        val result=engine.shoot(letter)
        if(result==Shot.IGNORED)return
        val now=SystemClock.uptimeMillis()
        val end=PointF(box?.centerX() ?: width*.7f, box?.bottom?.minus(d(12f)) ?: laneY(target.lane))
        bullets.add(Bullet(letter.uppercaseChar(),PointF(d(47f),laneY(target.lane)),end,now,result!=Shot.WRONG))
        when(result) {
            Shot.WRONG -> { wrongIndex=target.index;wrongUntil=now+350;message="Sai chữ • Giữ nguyên tiến độ";messageUntil=now+650 }
            Shot.COMPLETE -> {
                bursts.add(Burst(end,now,engine.combo))
                message=if(engine.combo>=5) "COMBO ${engine.combo}!" else "Hạ quái!"
                messageUntil=now+900;onSpoken?.invoke(engine.words[target.index].english)
            }
            else -> {}
        }
        onChanged?.invoke();requestFocus();invalidate();finish()
    }
    private fun finish() { if(engine.ended && !sent) { sent=true;post { onFinished?.invoke() } } }
    override fun onAttachedToWindow() { super.onAttachedToWindow();previous=0;invalidate() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility);previous=0 }
    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        val now=SystemClock.uptimeMillis()
        val delta=if(previous==0L) 0f else ((now-previous)/1000f).coerceIn(0f,.1f);previous=now
        if(!engine.paused && !engine.ended) {
            val before=engine.state.outcomes.size;engine.tick(delta)
            if(engine.state.outcomes.size>before) {
                engine.state.outcomes.drop(before).filter { !it.solved }.lastOrNull()?.let {
                    val word=engine.words.first { word -> word.id==it.id }
                    message="Lọt căn cứ: ${word.english}";messageUntil=now+1400;onSpoken?.invoke(word.english)
                }
                onChanged?.invoke()
            }
            if(now-savedAt>700) { savedAt=now;onChanged?.invoke() }
        }
        val w=width.toFloat();val h=height.toFloat()
        val grass=if(Palette.light) intArrayOf(0xFFE3F4DF.toInt(),0xFFC9E5C8.toInt()) else intArrayOf(0xFF183B35.toInt(),0xFF102F2D.toInt())
        p.shader=LinearGradient(0f,0f,w,h,grass,null,Shader.TileMode.CLAMP)
        c.drawRoundRect(0f,0f,w,h,d(16f),d(16f),p);p.shader=null
        val laneHeight=(h-d(48f))/WordDefenseEngine.LANE_COUNT
        for(lane in 0 until WordDefenseEngine.LANE_COUNT) {
            val top=d(30f)+lane*laneHeight
            p.color=if(lane%2==0) 0x1639B880 else 0x163B9DAC
            c.drawRect(d(54f),top,w,top+laneHeight,p)
            p.color=if(Palette.light) 0xFF88AD83.toInt() else 0xFF38685A.toInt();p.strokeWidth=d(1f)
            c.drawLine(d(55f),top+laneHeight,w-d(8f),top+laneHeight,p)
            for(i in 1..7) {
                val x=d(55f)+(w-d(55f))*i/8f
                p.color=if(Palette.light) 0xFFABD0A2.toInt() else 0xFF245344.toInt()
                c.drawOval(x,top+laneHeight-d(10f),x+d(8f),top+laneHeight-d(5f),p)
            }
            // One leaf cannon per lane guarding the base.
            p.color=if(Palette.light) 0xFF8999AD.toInt() else 0xFF4C6578.toInt()
            c.drawRoundRect(d(7f),top+d(5f),d(29f),top+laneHeight-d(5f),d(4f),d(4f),p)
            p.color=if(engine.combo>=5) Palette.orange else 0xFF5EBD82.toInt()
            c.drawOval(d(18f),laneY(lane)-d(13f),d(42f),laneY(lane)+d(13f),p)
            c.drawRoundRect(d(31f),laneY(lane)-d(6f),d(51f),laneY(lane)+d(6f),d(5f),d(5f),p)
            p.color=0xFF183B35.toInt();c.drawCircle(d(31f),laneY(lane)-d(4f),d(2f),p)
        }
        text(c,if(engine.stage%5==0) "BOSS • 3 LỚP TỪ" else "ĐỢT ${minOf(4,engine.state.next/5+1)} / ${(engine.words.size+4)/5}",d(12f),d(19f),11f,if(Palette.light) Palette.green else 0xFF93DBBC.toInt())
        text(c,"CĂN CỨ",d(5f),h-d(6f),8f,Palette.muted)
        boxes.clear()
        engine.state.active.forEach { m ->
            val cardW=minOf(d(150f),(w-d(66f))*.56f)
            val x=d(58f)+(1f-m.progress)*(w-cardW-d(66f))
            val top=d(30f)+m.lane*laneHeight+d(2f)
            val rect=RectF(x,top,x+cardW,top+laneHeight-d(3f));boxes[m.index]=rect
            val selected=engine.state.targetIndex==m.index
            val shake=if(m.index==wrongIndex && now<wrongUntil) sin(now/20.0).toFloat()*d(3f) else 0f
            c.save();c.translate(shake,0f)
            p.color=if(selected) Palette.elevated else Palette.surface
            c.drawRoundRect(rect.left,rect.top,rect.right,rect.bottom-d(20f),d(8f),d(8f),p)
            p.style=Paint.Style.STROKE;p.strokeWidth=d(if(selected) 2f else 1f)
            p.color=if(m.index==wrongIndex && now<wrongUntil) Palette.red else if(selected) Palette.orange else Palette.line
            c.drawRoundRect(rect.left,rect.top,rect.right,rect.bottom-d(20f),d(8f),d(8f),p);p.style=Paint.Style.FILL
            val word=engine.words[m.index]
            val title=if(engine.learningMode=="TYPING") word.english.uppercase() else word.meaning
            paragraph(c,title,rect.left+d(6f),rect.top+d(3f),rect.width()-d(12f),11f,Palette.white,1)
            val rawMask=engine.masked(m)
            val mask=if(rawMask.length<=12) rawMask.toCharArray().joinToString(" ") else rawMask
            paragraph(c,mask,rect.left+d(5f),rect.top+d(18f),rect.width()-d(10f),if(mask.length>24) 9f else if(mask.length>14) 10f else 12f,Palette.blue,1,true)
            monster(c,rect.centerX(),rect.bottom-d(9f),engine.kind(m.index),selected,now)
            if(engine.kind(m.index)==MonsterKind.BOSS) text(c,"${engine.words.size-m.index} LỚP",rect.right-d(4f),rect.bottom-d(2f),8f,Palette.orange,Paint.Align.RIGHT)
            c.restore()
        }
        if(engine.state.slowRemaining>0) {
            p.color=0x354DCEFF;c.drawRoundRect(0f,0f,w,h,d(16f),d(16f),p)
            text(c,"❄ CHẬM ${ceil(engine.state.slowRemaining).toInt()}s",w-d(10f),d(19f),11f,Palette.blue,Paint.Align.RIGHT)
        }
        bullets.removeAll { now-it.start>320 }
        bullets.forEach { b ->
            val t=((now-b.start)/320f).coerceIn(0f,1f)
            val x=b.from.x+(b.to.x-b.from.x)*t;val y=b.from.y+(b.to.y-b.from.y)*t
            p.color=if(b.good) (if(engine.combo>=5) Palette.orange else Palette.green) else Palette.red
            c.drawCircle(x,y,d(9f),p);text(c,b.letter.toString(),x,y+d(4f),11f,Palette.onAccent,Paint.Align.CENTER)
        }
        bursts.removeAll { now-it.start>650 }
        bursts.forEach { burst ->
            val t=(now-burst.start)/650f;p.color=if(burst.combo>=5) Palette.orange else Palette.green;p.alpha=((1-t)*255).toInt()
            for(i in 0..9) c.drawCircle(burst.center.x+cos(i*PI/5).toFloat()*t*d(32f),burst.center.y+sin(i*PI/5).toFloat()*t*d(32f),d(3f)*(1-t),p)
            p.alpha=255
        }
        if(now<messageUntil) text(c,message,w/2,h-d(6f),if(engine.combo>=5) 14f else 11f,Palette.orange,Paint.Align.CENTER)
        if(engine.state.breakRemaining>0 && !engine.paused) text(c,"NGHỈ GIỮA ĐỢT • ${ceil(engine.state.breakRemaining).toInt()}",w/2,h/2,18f,Palette.white,Paint.Align.CENTER)
        if(engine.paused && !engine.ended) {
            p.color=Palette.gameOverlay;c.drawRoundRect(0f,0f,w,h,d(16f),d(16f),p)
            text(c,"BẢO VỆ PHÒNG TUYẾN",w/2,h/2-d(8f),18f,Palette.white,Paint.Align.CENTER)
            text(c,"Bấm Tiếp tục • Chạm quái để ngắm",w/2,h/2+d(17f),12f,Palette.muted,Paint.Align.CENTER)
        }
        finish()
        if(isShown && (!engine.paused || bullets.isNotEmpty() || bursts.isNotEmpty()))postInvalidateOnAnimation()
    }
    private fun monster(c: Canvas,x: Float,y: Float,kind: MonsterKind,selected: Boolean,now: Long) {
        val bob=sin(now/110.0).toFloat()*d(1.5f)
        val radius=d(if(kind==MonsterKind.BOSS) 14f else 11f)
        p.color=when(kind) { MonsterKind.RUNNER->0xFFF1A35E.toInt();MonsterKind.ARMORED->0xFF9E91D5.toInt();MonsterKind.BOSS->0xFFD47FBC.toInt();else->0xFF7CCBA8.toInt() }
        c.drawRoundRect(x-radius,y-radius+bob,x+radius,y+radius*.7f+bob,d(6f),d(6f),p)
        c.drawCircle(x-radius*.5f,y-radius+bob,radius*.5f,p);c.drawCircle(x+radius*.5f,y-radius+bob,radius*.5f,p)
        if(kind==MonsterKind.ARMORED || kind==MonsterKind.BOSS) {
            p.color=if(kind==MonsterKind.BOSS) 0xFFFFD578.toInt() else 0xFF7894AD.toInt()
            c.drawRoundRect(x-radius-d(2f),y-radius-d(5f)+bob,x+radius+d(2f),y-radius*.5f+bob,d(3f),d(3f),p)
        }
        p.color=Color.WHITE;c.drawCircle(x-radius*.45f,y-radius*.3f+bob,d(3.7f),p);c.drawCircle(x+radius*.4f,y-radius*.3f+bob,d(3.7f),p)
        p.color=0xFF273943.toInt();c.drawCircle(x-radius*.5f,y-radius*.25f+bob,d(1.7f),p);c.drawCircle(x+radius*.35f,y-radius*.25f+bob,d(1.7f),p)
        p.strokeWidth=d(2.5f);c.drawLine(x-d(5f),y+radius*.7f,x-d(8f),y+radius,p);c.drawLine(x+d(5f),y+radius*.7f,x+d(8f),y+radius,p)
        if(selected) { p.style=Paint.Style.STROKE;p.color=Palette.orange;p.strokeWidth=d(1.4f);c.drawCircle(x,y,radius+d(4f),p);p.style=Paint.Style.FILL }
    }
    private fun text(c: Canvas,value: String,x: Float,y: Float,size: Float,color: Int,align: Paint.Align=Paint.Align.LEFT) {
        p.color=color;p.textSize=d(size);p.typeface=Typeface.DEFAULT_BOLD;p.textAlign=align;c.drawText(value,x,y,p);p.textAlign=Paint.Align.LEFT
    }
    private fun paragraph(c: Canvas,value: String,x: Float,y: Float,width: Float,size: Float,color: Int,lines: Int,mono: Boolean=false) {
        val paint=TextPaint(Paint.ANTI_ALIAS_FLAG).apply { this.color=color;textSize=d(size);typeface=if(mono) Typeface.MONOSPACE else Typeface.DEFAULT_BOLD }
        val layout=StaticLayout.Builder.obtain(value,0,value.length,paint,width.toInt().coerceAtLeast(1)).setMaxLines(lines)
            .setAlignment(Layout.Alignment.ALIGN_CENTER).setEllipsize(android.text.TextUtils.TruncateAt.END).setIncludePad(false).build()
        c.save();c.translate(x,y);layout.draw(c);c.restore()
    }
    override fun onTouchEvent(e: MotionEvent): Boolean {
        if(e.action==MotionEvent.ACTION_UP) {
            boxes.entries.firstOrNull { it.value.contains(e.x,e.y) }?.let { engine.select(it.key);onChanged?.invoke();invalidate() }
            performClick();requestFocus()
        };return true
    }
    override fun performClick(): Boolean { super.performClick();return true }
}
