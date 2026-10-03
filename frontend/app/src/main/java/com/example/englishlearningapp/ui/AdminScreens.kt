package com.example.englishlearningapp.ui

import android.widget.EditText
import com.example.englishlearningapp.R
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class AdminFragment : ScreenFragment() {
    override fun render() {
        header("KHÔNG GIAN QUẢN TRỊ", "Tổng quan hệ thống", "Giao diện Admin dùng dữ liệu mẫu cục bộ.",true)
        val badge=column(color=Palette.elevated)
        text("▦  ADMIN DEMO",14,Palette.purple,true,badge)
        text("Chưa có phân quyền hay đăng nhập Admin thật. Các thao tác chỉ chỉnh sửa danh sách quản trị mẫu trên máy, độc lập với kho từ học tập.",13,Palette.muted,parent=badge)
        stats(store.adminItems("users").size.toString() to "Người dùng mẫu",store.adminItems("words").size.toString() to "Từ vựng mẫu")
        tile("♙","Người dùng","Xem, thêm, sửa và xóa hồ sơ mẫu") { go(R.id.adminListFragment,"kind" to "users") }
        tile("📚","Kho từ vựng","Quản lý danh sách từ mẫu") { go(R.id.adminListFragment,"kind" to "words") }
        tile("▦","Chủ đề","Quản lý danh sách chủ đề") { go(R.id.adminListFragment,"kind" to "topics") }
        tile("✦","Câu hỏi Quiz","Quản lý danh sách dạng câu hỏi") { go(R.id.adminListFragment,"kind" to "quiz") }
        tile("✎","Nội dung học tập","Quản lý tiêu đề bài học mẫu") { go(R.id.adminListFragment,"kind" to "content") }
        tile("↗","Thống kê học tập trên máy","Xem tiến độ của hồ sơ hiện tại") { go(R.id.progressFragment) }
    }
}

class AdminListFragment : ScreenFragment() {
    private val kind get()=arguments?.getString("kind") ?: "words"
    override fun render() {
        val title=when(kind) { "users" -> "Người dùng"; "topics" -> "Chủ đề"; "quiz" -> "Câu hỏi Quiz"; "content" -> "Nội dung học tập"; else -> "Kho từ vựng" }
        header("QUẢN TRỊ MẪU",title,"Danh sách độc lập để thử giao diện quản lý.",true)
        button("＋  Thêm mục mới",Palette.purple) { edit(null) }
        val items=store.adminItems(kind)
        text("${items.size} mục",13,Palette.muted)
        if(items.isEmpty()) notice("Danh sách trống. Bấm Thêm mục mới để tạo dữ liệu mẫu.")
        items.forEachIndexed { index, item ->
            val card=column(color=Palette.surface)
            text(item,17,bold=true,parent=card)
            button("Chỉnh sửa",outlined=true,parent=card) { edit(index) }
            button("Xóa",Palette.orange,card,outlined=true) {
                MaterialAlertDialogBuilder(requireContext()).setTitle("Xóa mục này?").setMessage(item)
                    .setNegativeButton("Hủy",null).setPositiveButton("Xóa") { _, _ ->
                        store.saveAdminItems(kind,store.adminItems(kind).toMutableList().apply { removeAt(index) }); refresh()
                    }.show()
            }
        }
    }
    private fun edit(index: Int?) {
        val items=store.adminItems(kind).toMutableList()
        val input=EditText(requireContext()).apply {
            setText(if(index==null) "" else items[index]); hint="Tên hoặc mô tả mục"; setSingleLine()
            setPadding(dp(24),dp(16),dp(24),dp(16))
        }
        val dialog=MaterialAlertDialogBuilder(requireContext()).setTitle(if(index==null) "Thêm mục mẫu" else "Sửa mục mẫu")
            .setView(input).setNegativeButton("Hủy",null).setPositiveButton("Lưu",null).create()
        dialog.setOnShowListener {
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val value=input.text.toString().trim()
                if(value.isEmpty()) input.error="Nhập nội dung trước khi lưu"
                else {
                    if(index==null) items.add(value) else items[index]=value
                    store.saveAdminItems(kind,items); dialog.dismiss(); refresh()
                }
            }
        }
        dialog.show()
    }
}
