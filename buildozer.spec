[app]
title = Pseudo Clinic
package.name = pseudoclinic
package.domain = org.pseudoclinic
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_patterns = pseudo_clinic.py,content_cache.json
version = 0.1
icon.filename = %(source.dir)s/mascot.png
requirements = python3,kivy,openssl,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
