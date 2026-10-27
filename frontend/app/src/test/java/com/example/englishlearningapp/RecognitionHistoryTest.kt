package com.example.englishlearningapp

import com.example.englishlearningapp.data.model.RecognitionHistoryCodec
import com.example.englishlearningapp.data.model.RecognitionHistoryEntry
import com.example.englishlearningapp.data.model.Word
import org.junit.Assert.*
import org.junit.Test

class RecognitionHistoryTest {
    private val apple=Word("3","apple","/æpəl/","quả táo","","","food","🍎")
    @Test fun legacyNamesAndIdsResolveToTheSameWord() {
        for (raw in listOf("apple|27/10/2026", "3|27/10/2026")) {
            val entry=RecognitionHistoryCodec.decode(raw) { if(it=="apple" || it=="3") apple else null }!!
            assertEquals("apple",entry.word);assertEquals("3",entry.vocabularyId);assertEquals("quả táo",entry.meaning)
        }
    }
    @Test fun historyRemainsVisibleWithoutACatalogCache() {
        val entry=RecognitionHistoryCodec.decode("pomegranate|27/10/2026") { null }!!
        assertEquals("pomegranate",entry.word);assertNull(entry.vocabularyId)
    }
    @Test fun snapshotPreservesVietnameseAndSeparators() {
        val value=RecognitionHistoryEntry("55","computer mouse","/maʊs/","chuột máy tính | đồ vật","27/10/2026")
        assertEquals(value,RecognitionHistoryCodec.decode(RecognitionHistoryCodec.encode(value)) { null })
    }
    @Test fun malformedSnapshotsDoNotCrashTheScreen() {
        assertNull(RecognitionHistoryCodec.decode("{broken") { null })
        assertNull(RecognitionHistoryCodec.decode("{}") { null })
        assertNull(RecognitionHistoryCodec.decode("") { null })
    }
}
