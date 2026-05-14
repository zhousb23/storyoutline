[app]
title = StoryOutline
package.name = storyoutline
package.domain = com.storyoutline
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0.0
requirements = python3,kivy==2.3.1,kivymd==2.0.0,requests,chardet
presplash.color = #F0F6FB
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True
p4a.hostpython_version = 3.11
orientation = portrait
fullscreen = 0
log_level = 2


[buildozer]
log_level = 2
