param([string]$Adb = 'D:\PhanMem\AndroidStudioSDK\platform-tools\adb.exe')
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $PSScriptRoot 'screenshots'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
function Read-Ui {
    & $Adb shell uiautomator dump /sdcard/lenslearn-ui.xml | Out-Null
    [xml]$tree = (& $Adb shell cat /sdcard/lenslearn-ui.xml) -join "`n"
    return $tree
}
function Tap-Text([string]$Label) {
    for ($attempt = 0; $attempt -lt 7; $attempt++) {
        $tree = Read-Ui
        $node = $tree.SelectNodes('//node') | Where-Object { $_.text -eq $Label } | Select-Object -First 1
        if ($null -ne $node -and $node.bounds -match '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {
            $tapX = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
            $tapY = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
            & $Adb shell input tap $tapX $tapY
            Start-Sleep -Milliseconds 500
            return
        }
        & $Adb shell input swipe 540 1800 540 800 250
    }
    throw "Cannot find UI text: $Label"
}
function Capture([string]$Name) {
    & $Adb shell screencap -p /sdcard/lenslearn-screen.png
    & $Adb pull /sdcard/lenslearn-screen.png (Join-Path $outputDir "$Name.png") | Out-Null
    Write-Output "Captured $Name"
}
& $Adb install -r (Join-Path $projectDir 'app/build/outputs/apk/debug/app-debug.apk')
& $Adb shell am start -n com.example.englishlearningapp/.MainActivity
Start-Sleep -Seconds 1
$tree = Read-Ui
if (($tree.SelectNodes('//node') | Where-Object { $_.text -eq 'Thế giới quanh bạn, từ vựng của bạn.' }).Count -gt 0 -or
    ($tree.SelectNodes('//node') | Where-Object { $_.text -eq 'Đăng nhập trải nghiệm  →' }).Count -gt 0) {
    Capture '01-login'
    Tap-Text 'Khám phá bằng hồ sơ mẫu'
    Tap-Text 'Bắt đầu khám phá  →'
}
Capture '02-home'
Tap-Text 'Nhận diện'
Capture '03-camera'
Tap-Text 'Thử với ảnh minh họa'
Capture '04-recognition'
Tap-Text 'Apple'
Capture '05-word-detail'
& $Adb shell input keyevent KEYCODE_BACK
& $Adb shell input keyevent KEYCODE_BACK
Tap-Text 'Từ vựng'
Capture '06-vocabulary'
Tap-Text 'Luyện tập'
Capture '07-practice'
Tap-Text 'Bắt đầu Flashcard  →'
Capture '08-flashcard'
& $Adb shell input keyevent KEYCODE_BACK
Tap-Text 'Nhìn ảnh chọn từ'
Capture '09-quiz'
& $Adb shell input keyevent KEYCODE_BACK
Tap-Text 'Dừng'
Tap-Text 'Hồ sơ'
Capture '10-profile'
Tap-Text 'Tiến độ học tập'
Capture '11-progress'
& $Adb shell input keyevent KEYCODE_BACK
Tap-Text 'Khu quản trị mẫu'
Capture '12-admin'
& $Adb shell input keyevent KEYCODE_BACK
Tap-Text 'Trang chủ'
