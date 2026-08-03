[app]

title = Мосбиржа Сигналы
package.name = moexsignals
package.domain = com.moex.trader
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
version = 1.0
requirements = python3,kivy,requests,plyer,pytz
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS
android.api = 34
android.minapi = 21
android.targetapi = 34
android.archs = arm64-v8a, armeabi-v7a
orientation = portrait
fullscreen = 0
log_level = 2
android.accept_sdk_license = True
android.ndk = 27
android.sdk = 34
presplash.color = #1a1a2e
android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk
android.ndk_path = /home/runner/.buildozer/android/platform/android-ndk-r27

[buildozer]
build_dir = ./.buildozer
bin_dir = ./bin
log_level = 2
warn_on_root = 1
