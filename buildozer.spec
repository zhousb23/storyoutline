[app]
title = StoryOutline
package.name = storyoutline
package.domain = com.storyoutline
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
source.exclude_exts = spec
source.include_patterns = src/*,src/ui/*
version = 1.0.0
requirements = python3,kivy==2.3.1,kivymd==2.0.0,requests==2.32.0,chardet==5.2.0,python-docx==1.1.0,lxml==5.3.0,pdfplumber==0.11.0,pillow==11.0.0,beautifulsoup4==4.12.0,ebooklib==0.18
presplash.color = #F0F6FB
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 26
android.ndk = 25b
android.sdk = 34
android.gradle_dependencies =
android.enable_androidx = True
orientation = portrait
fullscreen = 0
log_level = 2
warn_on_root = 1

# 主入口
main.py = src/kivy_app.py

[buildozer]
log_level = 2
warn_on_root = 1
