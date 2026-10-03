package com.example.englishlearningapp.ui

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import android.view.inputmethod.InputMethodManager
import androidx.core.os.bundleOf
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.MainActivity
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.Word
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout

object Palette {
    val background = Color.rgb(25,25,46)
    val surface = Color.rgb(32,35,56)
    val elevated = Color.rgb(41,45,76)
    val line = Color.rgb(53,59,96)
    val blue = Color.rgb(65,157,222)
    val purple = Color.rgb(161,109,245)
    val green = Color.rgb(49,204,137)
    val orange = Color.rgb(255,184,91)
    val red = Color.rgb(211,55,75)
    val white = Color.rgb(246,247,252)
    val muted = Color.rgb(167,175,201)
}

fun Context.dp(value: Int) = (value * resources.displayMetrics.density).toInt()
fun rounded(color: Int, radius: Float = 20f, stroke: Int = Palette.line) = GradientDrawable().apply {
    setColor(color); cornerRadius = radius; setStroke(1, stroke)
}

/** Shared native Views keep spacing, contrast and button behavior consistent across XML screens. */
open class ScreenFragment : Fragment(R.layout.fragment_screen) {
    private var screenContent: LinearLayout? = null
    protected val content get() = requireNotNull(screenContent)
    protected val store get() = (requireActivity() as MainActivity).store
    protected val words get() = (requireActivity() as MainActivity).words
    protected val quizzes get() = (requireActivity() as MainActivity).quizzes
    protected fun go(id: Int, vararg args: Pair<String, Any?>) {
        if (!isAdded || findNavController().currentDestination?.id != destinationId) return
        hideKeyboard()
        findNavController().navigate(id, bundleOf(*args))
    }
    private var destinationId: Int? = null
    protected fun toast(message: String) = Toast.makeText(requireContext(), message, Toast.LENGTH_SHORT).show()
    protected fun speak(text: String) = (requireActivity() as MainActivity).speak(text)
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        screenContent = view.findViewById(R.id.screen_content)
        destinationId = findNavController().currentDestination?.id
        render()
    }
    protected open fun render() {}
    override fun onDestroyView() {
        screenContent = null
        destinationId = null
        super.onDestroyView()
    }
    protected fun refresh(keepScrollPosition: Boolean = true) {
        if (screenContent == null) return
        val scroll = view?.findViewById<androidx.core.widget.NestedScrollView>(R.id.screen_scroll)
        val position = if (keepScrollPosition) scroll?.scrollY ?: 0 else 0
        content.removeAllViews(); render()
        scroll?.post { scroll.scrollTo(0, position) }
    }
    protected fun hideKeyboard() {
        val manager = requireContext().getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        view?.let { manager.hideSoftInputFromWindow(it.windowToken, 0); it.clearFocus() }
    }
    protected fun column(parent: LinearLayout = content, color: Int? = null, padding: Int = 18): LinearLayout = LinearLayout(requireContext()).apply {
        orientation = LinearLayout.VERTICAL
        if (color != null) { background = rounded(color, requireContext().dp(22).toFloat()); setPadding(dp(padding), dp(padding), dp(padding), dp(padding)) }
        parent.addView(this, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })
    }
    protected fun row(parent: LinearLayout = content): LinearLayout = LinearLayout(requireContext()).apply {
        orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
        parent.addView(this, LinearLayout.LayoutParams(-1,-2).apply { bottomMargin = dp(10) })
    }
    protected fun dp(v: Int) = requireContext().dp(v)
    protected fun text(value: String, size: Int = 16, color: Int = Palette.white, bold: Boolean = false,
                       parent: LinearLayout = content, center: Boolean = false): TextView = TextView(requireContext()).apply {
        text = value; textSize = size.toFloat(); setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
        if (center) gravity = Gravity.CENTER
        setLineSpacing(dp(3).toFloat(), 1f)
        parent.addView(this, LinearLayout.LayoutParams(-1,-2).apply { bottomMargin = dp(8) })
    }
    protected fun header(kicker: String, title: String, subtitle: String = "", back: Boolean = false) {
        if (back) text("‹  Quay lại", 15, Palette.blue).apply {
            minHeight = dp(48); gravity = Gravity.CENTER_VERTICAL
            setOnClickListener { findNavController().popBackStack() }
        }
        text(kicker.uppercase(), 11, Palette.blue, true).letterSpacing = 0.16f
        text(title, 29, bold = true)
        if (subtitle.isNotEmpty()) text(subtitle, 14, Palette.muted)
        space(12)
    }
    protected fun space(height: Int) { content.addView(View(requireContext()), LinearLayout.LayoutParams(1,dp(height))) }
    protected fun section(title: String, action: String? = null, onAction: (() -> Unit)? = null) {
        val r = row()
        text(title, 18, bold = true, parent = r).layoutParams = LinearLayout.LayoutParams(0,-2,1f)
        if (action != null) text(action, 13, Palette.blue, parent = r).apply {
            layoutParams = LinearLayout.LayoutParams(-2,dp(48)); gravity = Gravity.CENTER
            setOnClickListener { onAction?.invoke() }
        }
    }
    protected fun button(label: String, color: Int = Palette.blue, parent: LinearLayout = content,
                         outlined: Boolean = false, action: () -> Unit): MaterialButton = MaterialButton(requireContext()).apply {
        text = label; isAllCaps = false; textSize = 15f; cornerRadius = dp(15)
        insetTop = 0; insetBottom = 0
        backgroundTintList = ColorStateList.valueOf(if (outlined) Palette.elevated else color)
        setTextColor(if (outlined) color else Palette.white)
        if (outlined) { strokeWidth = dp(1); strokeColor = ColorStateList.valueOf(Palette.line) }
        minHeight = dp(54)
        setPadding(dp(16),dp(10),dp(16),dp(10))
        parent.addView(this, LinearLayout.LayoutParams(-1,-2).apply { topMargin = dp(5); bottomMargin = dp(9) })
        setOnClickListener { action() }
    }
    protected fun field(label: String, initial: String = "", password: Boolean = false,
                        parent: LinearLayout = content, viewId: Int = View.NO_ID): TextInputEditText {
        val wrapper = TextInputLayout(requireContext()).apply {
            hint = label; boxBackgroundMode = TextInputLayout.BOX_BACKGROUND_OUTLINE
            boxStrokeColor = Palette.blue
            setBoxCornerRadii(dp(14).toFloat(),dp(14).toFloat(),dp(14).toFloat(),dp(14).toFloat())
            if (password) endIconMode = TextInputLayout.END_ICON_PASSWORD_TOGGLE
        }
        val edit = TextInputEditText(wrapper.context).apply {
            id = viewId
            // Passwords are intentionally not written to saved view state.
            isSaveEnabled = !password && viewId != View.NO_ID
            setText(initial); setTextColor(Palette.white); textSize = 15f; setSingleLine()
            inputType = if (password) 129 else 1
            setPadding(dp(15),dp(17),dp(15),dp(17))
        }
        wrapper.addView(edit)
        parent.addView(wrapper, LinearLayout.LayoutParams(-1,-2).apply { bottomMargin = dp(16) })
        return edit
    }
    protected fun tile(symbol: String, title: String, subtitle: String, color: Int = Palette.blue, action: () -> Unit) {
        val card = column(color = Palette.surface)
        val r = row(card)
        text(symbol, 27, parent = r, center = true).apply { layoutParams = LinearLayout.LayoutParams(dp(48),dp(48)) }
        val labels = LinearLayout(requireContext()).apply { orientation = LinearLayout.VERTICAL }
        r.addView(labels, LinearLayout.LayoutParams(0,-2,1f).apply { marginStart = dp(12) })
        text(title, 16, bold = true, parent = labels)
        text(subtitle, 12, Palette.muted, parent = labels)
        text("›", 26, color, parent = r).layoutParams = LinearLayout.LayoutParams(dp(20),-2)
        card.isClickable = true; card.isFocusable = true; card.contentDescription = "$title. $subtitle"
        card.setOnClickListener { action() }
    }
    protected fun wordRow(word: Word, parent: LinearLayout = content, showSaveLabel: Boolean = false) {
        val card = column(parent, Palette.surface, 14)
        val r = row(card)
        text(word.symbol, 30, parent = r, center = true).layoutParams = LinearLayout.LayoutParams(dp(50),dp(50))
        val labels = LinearLayout(requireContext()).apply { orientation = LinearLayout.VERTICAL }
        r.addView(labels, LinearLayout.LayoutParams(0,-2,1f).apply { marginStart = dp(12) })
        text(word.english, 17, bold = true, parent = labels)
        text("${word.ipa}  •  ${word.meaning}", 12, Palette.muted, parent = labels)
        val saved = word.id in store.saved
        if (showSaveLabel) {
            button(if (saved) "✓  Đã lưu • Bỏ lưu" else "＋  Lưu vào bộ sưu tập",
                parent = card, outlined = true) {
                hideKeyboard(); store.toggleSave(word.id)
                toast(if (saved) "Đã bỏ lưu ${word.english}" else "Đã lưu ${word.english}")
                refresh()
            }.contentDescription = if (saved) "Đã lưu ${word.english}. Bấm để bỏ lưu" else "Lưu ${word.english} vào bộ sưu tập"
        } else {
            text(if (saved) "★" else "＋", 22, Palette.blue, parent = r).apply {
                gravity = Gravity.CENTER; layoutParams = LinearLayout.LayoutParams(dp(48),dp(48))
                contentDescription = if (saved) "Bỏ lưu ${word.english}" else "Lưu ${word.english}"
                setOnClickListener { hideKeyboard(); store.toggleSave(word.id); refresh() }
            }
        }
        card.isFocusable = true
        card.setOnClickListener { go(R.id.wordDetailFragment, "wordId" to word.id) }
    }
    protected fun stats(vararg values: Pair<String, String>) {
        val r = row()
        values.forEachIndexed { i, (value, label) ->
            val cell = LinearLayout(requireContext()).apply {
                orientation = LinearLayout.VERTICAL; background = rounded(Palette.surface, dp(18).toFloat())
                setPadding(dp(12),dp(16),dp(12),dp(12))
            }
            r.addView(cell, LinearLayout.LayoutParams(0,-2,1f).apply { if (i > 0) marginStart = dp(10) })
            text(value, 24, listOf(Palette.blue,Palette.purple,Palette.green)[i % 3], true, cell)
            text(label, 11, Palette.muted, parent = cell)
        }
    }
    protected fun progress(value: Int, max: Int, parent: LinearLayout = content, color: Int = Palette.blue) {
        val bar = com.google.android.material.progressindicator.LinearProgressIndicator(requireContext()).apply {
            this.max = max.coerceAtLeast(1); setProgressCompat(value, false)
            trackThickness = dp(7); trackCornerRadius = dp(4); trackColor = Palette.elevated; setIndicatorColor(color)
        }
        parent.addView(bar, LinearLayout.LayoutParams(-1,dp(8)).apply { topMargin=dp(6); bottomMargin=dp(16) })
    }
    protected fun notice(message: String) { text(message, 12, Palette.muted) }
}
