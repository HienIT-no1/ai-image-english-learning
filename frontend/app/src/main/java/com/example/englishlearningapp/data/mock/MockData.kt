package com.example.englishlearningapp.data.mock

import com.example.englishlearningapp.data.model.Topic
import com.example.englishlearningapp.data.model.Word

/** Offline fixtures. Real recognition will come from the Java backend in a later phase. */
object MockData {
    val topics = listOf(Topic("food", "Đồ ăn & thức uống", "🍎"), Topic("home", "Đồ vật quanh ta", "🪑"),
        Topic("nature", "Thiên nhiên", "🌿"), Topic("animals", "Động vật", "🐈"))
    val words = listOf(
        Word("apple", "Apple", "/ˈæp.əl/", "Quả táo", "An apple a day keeps the doctor away.", "Mỗi ngày một quả táo giúp bạn khỏe mạnh.", "food", "🍎"),
        Word("coffee", "Coffee", "/ˈkɒf.i/", "Cà phê", "I drink coffee every morning.", "Tôi uống cà phê mỗi sáng.", "food", "☕"),
        Word("bread", "Bread", "/bred/", "Bánh mì", "She buys fresh bread for breakfast.", "Cô ấy mua bánh mì mới cho bữa sáng.", "food", "🍞"),
        Word("book", "Book", "/bʊk/", "Quyển sách", "This book is very interesting.", "Quyển sách này rất thú vị.", "home", "📚"),
        Word("chair", "Chair", "/tʃeər/", "Cái ghế", "Please sit on this chair.", "Hãy ngồi lên chiếc ghế này.", "home", "🪑"),
        Word("lamp", "Lamp", "/læmp/", "Đèn", "The lamp is on the desk.", "Chiếc đèn ở trên bàn.", "home", "💡"),
        Word("tree", "Tree", "/triː/", "Cây", "There is a tall tree in the garden.", "Có một cây cao trong vườn.", "nature", "🌳"),
        Word("flower", "Flower", "/ˈflaʊ.ər/", "Bông hoa", "This flower smells wonderful.", "Bông hoa này có mùi rất thơm.", "nature", "🌷"),
        Word("cat", "Cat", "/kæt/", "Con mèo", "The cat is sleeping on the sofa.", "Con mèo đang ngủ trên ghế sofa.", "animals", "🐈"),
        Word("dog", "Dog", "/dɒɡ/", "Con chó", "My dog loves to play outside.", "Chó của tôi thích chơi bên ngoài.", "animals", "🐕"),
        Word("bird", "Bird", "/bɜːd/", "Con chim", "A bird is singing in the tree.", "Một chú chim đang hót trên cây.", "animals", "🐦"),
        Word("banana", "Banana", "/bəˈnɑː.nə/", "Quả chuối", "I eat a banana after running.", "Tôi ăn một quả chuối sau khi chạy.", "food", "🍌")
    )
}

