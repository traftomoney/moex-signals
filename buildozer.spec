[app]

# Название приложения
title = Мосбиржа Сигналы

# Имя пакета
package.name = moexsignals

# Домен
package.domain = com.moex.trader

# Главный файл
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# Версия
version = 1.0

# Требования для Android
requirements = python3,kivy,requests,plyer,pytz,android

# Разрешения
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS

# API уровни
android.api = 34
android.minapi = 21
android.targetapi = 34

# Архитектуры
android.archs = arm64-v8a, armeabi-v7a

# Ориентация
orientation = portrait
fullscreen = 0

# Логи
log_level = 2

# Разное
android.accept_sdk_license = True
android.ndk = 27
android.sdk = 34

# Цвета
presplash.color = #1a1a2e

# Настройки сборки
[buildozer]
build_dir = ./.buildozer
bin_dir = ./bin
log_level = 2
warn_on_root = 1