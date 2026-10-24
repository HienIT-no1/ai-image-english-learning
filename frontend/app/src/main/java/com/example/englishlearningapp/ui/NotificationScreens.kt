package com.example.englishlearningapp.ui

import android.os.Bundle
import android.view.View
import androidx.lifecycle.lifecycleScope
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.mapper.toWord
import kotlinx.coroutines.launch

class NotificationsFragment : ScreenFragment() {
    private var items=emptyList<NotificationDto>()
    private var unread=0
    private var loading=true
    private var more=false
    private var failure: String?=null
    override fun onViewCreated(view: View,state: Bundle?) { super.onViewCreated(view,state);load() }
    private fun load(append: Boolean=false) {
        loading=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            notifications.inbox(if(append) items.size else 0).onSuccess { page ->
                items=if(append) (items+page.items).distinctBy { it.notificationId } else page.items
                unread=page.unreadCount;more=page.items.size==50
            }.onFailure { failure=it.message }
            loading=false;refresh()
        }
    }
    override fun render() {
        header("LENSLEARN NHẮC BẠN","Thông báo","$unread thông báo chưa đọc",true)
        button("Ôn tập các từ đến hạn",Palette.purple) { go(R.id.dueReviewFragment) }
        if(items.isNotEmpty()) button("Đánh dấu tất cả đã đọc",outlined=true) {
            viewLifecycleOwner.lifecycleScope.launch { notifications.readAll().onSuccess { load() }.onFailure { toast(it.message ?: "Không cập nhật được.") } }
        }
        failure?.let { notice(it);button("Thử lại") { load() } }
        if(loading) notice("Đang tải thông báo…")
        else if(items.isEmpty() && failure==null) notice("Chưa có thông báo. Bật nhắc học và chọn giờ trong Cài đặt để nhận lời nhắc hằng ngày.")
        items.forEach { item ->
            tile(if(item.readAt==null) "●" else "✓",item.title,
                "${item.occurrenceDate} • ${if(item.readAt==null) "Chưa đọc" else "Đã đọc"}\n${item.body}",Palette.blue) {
                viewLifecycleOwner.lifecycleScope.launch {
                    notifications.read(item.notificationId).onSuccess { go(R.id.dueReviewFragment) }
                        .onFailure { toast(it.message ?: "Chưa mở được thông báo.") }
                }
            }
        }
        if(more && !loading) button("Xem thông báo cũ hơn",outlined=true) { load(true) }
        button("Cài đặt nhắc học",outlined=true) { go(R.id.settingsFragment) }
    }
}

class DueReviewFragment : ScreenFragment() {
    private var data=emptyList<VocabularyDto>()
    private var loading=true
    private var failure: String?=null
    override fun onViewCreated(view: View,state: Bundle?) { super.onViewCreated(view,state);load() }
    override fun onResume() { super.onResume();if(!loading) load() }
    private fun load() {
        loading=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            notifications.due().onSuccess { data=it;learning.load() }.onFailure { failure=it.message }
            loading=false;refresh()
        }
    }
    override fun render() {
        header("NHỚ LÂU HƠN MỖI NGÀY","Ôn tập đến hạn","Ưu tiên từ chưa học và những từ đã đến lịch ôn tiếp.",true)
        if(loading) { notice("Đang lấy từ đến hạn từ máy chủ…");return }
        failure?.let { notice(it);button("Thử lại") { load() };return }
        if(data.isEmpty()) {
            text("Bạn đã ôn xong!",25,Palette.green,true)
            notice("Hiện không có từ đến hạn. Bạn có thể lưu thêm từ hoặc luyện tập tự do.")
            button("Khám phá từ vựng") { go(R.id.topicsFragment) }
            button("Luyện tập tự do",outlined=true) { go(R.id.practiceFragment) };return
        }
        text("${data.size} từ trong lượt ôn này",19,Palette.purple,true)
        button("Bắt đầu ôn ${data.size} từ",Palette.purple) {
            go(R.id.flashcardFragment,"wordIds" to ArrayList(data.map { it.vocabularyId.toString() }))
        }
        notice("Đúng: ôn sau 1, 3, 7 ngày, rồi tăng dần tối đa 30 ngày. Chưa nhớ: nhắc ôn lại sau 10 phút. Danh sách tải tối đa 100 từ mỗi lượt.")
        data.forEach { wordRow(it.toWord()) }
    }
}
