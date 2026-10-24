package com.example.englishlearningapp.data.local

import android.content.Context

/** Appearance belongs to this device, including the sign-in screen. */
class AppAppearance(context: Context) {
    private val prefs=context.getSharedPreferences("appearance",Context.MODE_PRIVATE)
    var light: Boolean
        get()=prefs.getBoolean("light",false)
        set(value) { prefs.edit().putBoolean("light",value).apply() }
}
