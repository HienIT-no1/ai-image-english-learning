package com.example.englishlearningapp.ui

import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.lifecycle.lifecycleScope
import com.example.englishlearningapp.MainActivity
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.*
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.launch

abstract class AdminScreen : ScreenFragment() {
    protected var loading=true
    protected var failure: String?=null
    protected abstract suspend fun fetch()
    protected abstract fun clearData()
    override fun onViewCreated(view: View,savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState);reload()
    }
    protected fun reload() {
        loading=true;failure=null;clearData();refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            try { fetch() }
            catch (error: kotlinx.coroutines.CancellationException) { throw error }
            catch (error: Exception) { clearData();failure=error.message ?: "Không tải được dữ liệu quản trị." }
            loading=false;refresh()
        }
    }
    protected fun ready(): Boolean {
        if (!store.isAdmin) {
            notice("Tài khoản không có quyền quản trị. Quyền được kiểm tra bởi máy chủ.")
            button("Về trang học tập") { go(R.id.homeFragment) }
            return false
        }
        if (loading) { notice("Đang tải dữ liệu quản trị…");return false }
        failure?.let {
            notice(it);button("Thử lại") { reload() }
            button("Về trang học tập",outlined=true) { go(R.id.homeFragment) }
            return false
        }
        return true
    }
}

class AdminFragment : AdminScreen() {
    private var data: AdminSummaryDto?=null
    override fun clearData() { data=null }
    override suspend fun fetch() { data=admin.summary().getOrThrow() }
    override fun render() {
        header("KHÔNG GIAN QUẢN TRỊ","Tổng quan hệ thống","Xin chào ${store.name}. Dữ liệu lấy từ PostgreSQL.")
        if (!ready()) return
        val summary=data ?: return
        stats(summary.users.toString() to "Tài khoản",summary.vocabularies.toString() to "Từ vựng",summary.topics.toString() to "Chủ đề")
        notice("${summary.admins} Admin • ${summary.completedQuizzes} bài Quiz đã hoàn thành")
        tile("♙","Người dùng","Xem tài khoản và quyền USER/ADMIN") { go(R.id.adminListFragment,"kind" to "users") }
        tile("📚","Kho từ vựng","Thêm, sửa từ, nghĩa, ví dụ và chủ đề") { go(R.id.adminListFragment,"kind" to "words") }
        tile("▦","Chủ đề","Thêm, sửa và xóa chủ đề trống") { go(R.id.adminListFragment,"kind" to "topics") }
        button("Làm mới thống kê",outlined=true) { reload() }
        button("Về trang học tập",Palette.green) { go(R.id.homeFragment) }
        button("Đăng xuất",Palette.orange,outlined=true) { (requireActivity() as MainActivity).logout() }
    }
}

class AdminListFragment : AdminScreen() {
    private val kind get()=arguments?.getString("kind") ?: "words"
    private var topics=emptyList<TopicDto>()
    private var users=emptyList<AdminUserDto>()
    private var vocabularies=emptyList<VocabularyDto>()
    private var offset=0
    private var editor: androidx.appcompat.app.AlertDialog?=null
    override fun clearData() { topics=emptyList();users=emptyList();vocabularies=emptyList() }
    override suspend fun fetch() {
        when(kind) {
            "users" -> users=admin.users(offset).getOrThrow()
            "topics" -> topics=admin.topics().getOrThrow()
            else -> { topics=admin.topics().getOrThrow();vocabularies=admin.words().getOrThrow() }
        }
    }
    override fun onDestroyView() { editor?.dismiss();editor=null;super.onDestroyView() }
    override fun render() {
        header("QUẢN TRỊ",when(kind) { "users"->"Người dùng";"topics"->"Chủ đề";else->"Kho từ vựng" },"Thay đổi được lưu trên máy chủ.",true)
        if (!ready()) return
        button("Tải lại danh sách",outlined=true) { reload() }
        when(kind) {
            "users" -> {
                notice("Tài khoản Admin được cấp bằng lệnh trên server. Màn hình này chỉ xem danh sách người dùng.")
                users.forEach { user ->
                    val card=column(color=Palette.surface)
                    text("${user.username} • ${user.role}",17,bold=true,parent=card)
                    text(user.fullName ?: "Chưa có tên hiển thị",14,parent=card)
                    text(user.email,13,Palette.muted,parent=card)
                }
                if (users.isEmpty()) notice("Không có tài khoản ở trang này.")
                if (offset>0) button("Trang trước",outlined=true) { offset=(offset-100).coerceAtLeast(0);reload() }
                if (users.size==100) button("Trang tiếp theo",outlined=true) { offset+=100;reload() }
            }
            "topics" -> {
                button("＋  Thêm chủ đề",Palette.purple) { editTopic(null) }
                text("${topics.size} chủ đề",13,Palette.muted)
                topics.forEach { topic ->
                    val card=column(color=Palette.surface)
                    text("${topic.symbol} ${topic.name}",17,bold=true,parent=card)
                    text("${topic.slug} • ${topic.vocabularyCount} từ",13,Palette.muted,parent=card)
                    button("Chỉnh sửa chủ đề",outlined=true,parent=card) { editTopic(topic) }.contentDescription="Chỉnh sửa chủ đề ${topic.name}"
                    button("Xóa chủ đề",Palette.orange,card,outlined=true) {
                        MaterialAlertDialogBuilder(requireContext()).setTitle("Xóa chủ đề?").setMessage(topic.name)
                            .setNegativeButton("Hủy",null).setPositiveButton("Xóa") { _,_ ->
                                viewLifecycleOwner.lifecycleScope.launch {
                                    admin.deleteTopic(topic.topicId).onSuccess { toast("Đã xóa chủ đề");reload() }
                                        .onFailure { toast(it.message ?: "Chưa xóa được chủ đề.");if(!store.isAdmin) refresh() }
                                }
                            }.show()
                    }
                }
            }
            else -> {
                button("＋  Thêm từ vựng",Palette.purple) { editWord(null) }
                notice("Sửa nghĩa và ví dụ chính; các nghĩa/ví dụ khác được giữ lại. Từ đã dùng để học được giữ để bảo toàn lịch sử.")
                text("${vocabularies.size} từ vựng",13,Palette.muted)
                vocabularies.forEach { word ->
                    val card=column(color=Palette.surface)
                    text(word.word,18,bold=true,parent=card)
                    text(word.meanings.firstOrNull()?.meaningVi ?: "Chưa có nghĩa",14,parent=card)
                    text(word.topics.joinToString { it.name }.ifBlank { "Chưa có chủ đề" },12,Palette.muted,parent=card)
                    button("Chỉnh sửa từ",outlined=true,parent=card) { editWord(word) }.contentDescription="Chỉnh sửa từ ${word.word}"
                }
            }
        }
    }
    private fun form(): LinearLayout = LinearLayout(requireContext()).apply {
        orientation=LinearLayout.VERTICAL;setPadding(dp(20),dp(12),dp(20),dp(12))
    }
    private fun dialog(title: String,form: LinearLayout,save: suspend () -> Unit) {
        val scroll=ScrollView(requireContext()).apply { addView(form) }
        val dialog=MaterialAlertDialogBuilder(requireContext()).setTitle(title).setView(scroll)
            .setNegativeButton("Hủy",null).setPositiveButton("Lưu",null).create()
        editor=dialog
        dialog.setOnShowListener {
            val submit=dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)
            submit.setOnClickListener {
                hideKeyboard();submit.isEnabled=false
                viewLifecycleOwner.lifecycleScope.launch {
                    try { save();words.loadFromApi();dialog.dismiss();toast("Đã lưu lên máy chủ");reload() }
                    catch (error: kotlinx.coroutines.CancellationException) { throw error }
                    catch (error: Exception) { toast(error.message ?: "Chưa lưu được dữ liệu.");if(!store.isAdmin) { dialog.dismiss();refresh() } }
                    finally { submit.isEnabled=true }
                }
            }
        }
        dialog.show()
    }
    private fun editTopic(topic: TopicDto?) {
        val form=form()
        val name=field("Tên chủ đề",topic?.name ?: "",parent=form,viewId=R.id.input_admin_name)
        val slug=field("Mã chủ đề (vd: school)",topic?.slug ?: "",parent=form,viewId=R.id.input_admin_slug)
        val symbol=field("Biểu tượng",topic?.symbol ?: "📚",parent=form,viewId=R.id.input_admin_symbol)
        dialog(if(topic==null) "Thêm chủ đề" else "Sửa chủ đề",form) {
            val body=AdminTopicRequest(name.text.toString().trim(),slug.text.toString().trim(),symbol.text.toString().trim())
            require(body.name.length in 1..100) { "Tên chủ đề từ 1 đến 100 ký tự." }
            require(body.slug.length in 1..50 && body.slug.matches(Regex("[a-z0-9]+(-[a-z0-9]+)*"))) { "Mã dùng chữ thường, số và dấu gạch nối." }
            require(body.symbol.length in 1..20) { "Nhập biểu tượng từ 1 đến 20 ký tự." }
            admin.saveTopic(topic?.topicId,body).getOrThrow()
        }
    }
    private fun editWord(word: VocabularyDto?) {
        val form=form()
        val spelling=field("Từ tiếng Anh",word?.word ?: "",parent=form,viewId=R.id.input_admin_word)
        val ipa=field("Phiên âm",word?.ipa ?: "",parent=form,viewId=R.id.input_admin_ipa)
        val meaning=field("Nghĩa tiếng Việt chính",word?.meanings?.firstOrNull()?.meaningVi ?: "",parent=form,viewId=R.id.input_admin_meaning)
        val example=word?.examples?.firstOrNull()
        val sentence=field("Câu ví dụ tiếng Anh",example?.sentenceEn ?: "",parent=form,viewId=R.id.input_admin_sentence)
        val translation=field("Dịch câu ví dụ",example?.sentenceVi ?: "",parent=form,viewId=R.id.input_admin_translation)
        val selected=word?.topics?.map { it.topicId }?.toMutableSet() ?: mutableSetOf()
        button("Chọn chủ đề",parent=form,outlined=true) {
            if(topics.isEmpty()) { toast("Hãy tạo chủ đề trước.");return@button }
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn chủ đề")
                .setMultiChoiceItems(topics.map { it.name }.toTypedArray(),topics.map { it.topicId in selected }.toBooleanArray()) { _,i,checked ->
                    if(checked) selected.add(topics[i].topicId) else selected.remove(topics[i].topicId)
                }.setPositiveButton("Xong",null).show()
        }
        dialog(if(word==null) "Thêm từ vựng" else "Sửa từ vựng",form) {
            val body=AdminWordRequest(spelling.text.toString().trim(),ipa.text.toString().trim(),meaning.text.toString().trim(),
                sentence.text.toString().trim(),translation.text.toString().trim(),selected.toList())
            require(body.word.length in 1..100 && body.meaningVi.length in 1..2000) { "Nhập từ tiếng Anh và nghĩa tiếng Việt." }
            require(body.ipa.length<=100 && body.sentenceEn.length<=2000 && body.sentenceVi.length<=2000) { "Phiên âm hoặc ví dụ quá dài." }
            admin.saveWord(word?.vocabularyId,body).getOrThrow()
        }
    }
}
