# -*- coding: utf-8 -*-
"""StoryOutline Android 版 — KivyMD 2.0 Material Design 3。"""

import os
import sys
import json
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'systemandmulti')

from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.card import MDCard
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogButtonContainer
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.appbar import MDTopAppBar, MDTopAppBarTitle, MDTopAppBarLeadingButtonContainer

from src.file_parser import parse_file
from src.chapter_splitter import split_chapters
from src.deepseek_client import DeepSeekClient
from src.analysis_pipeline import AnalysisPipeline
from src.result_manager import ProjectState, ResultManager
from src.utils import get_wenjian_dir, get_data_dir


# ============================================================
# KV 界面
# ============================================================

KV = '''
#:import os os
#:import get_wenjian_dir src.utils.get_wenjian_dir

<RootScreen>:
    md_bg_color: '#F5F7FA'

    MDTopAppBar:
        id: toolbar
        title: 'StoryOutline'
        pos_hint: {'top': 1}

    MDBoxLayout:
        orientation: 'vertical'
        padding: '16dp'
        spacing: '12dp'
        pos_hint: {'top': 0.92}
        size_hint_y: 0.88

        # === 顶部分页按钮 ===
        MDBoxLayout:
            spacing: '8dp'
            adaptive_height: True

            MDButton:
                style: 'filled' if app.current_tab == 'import' else 'outlined'
                on_release: app.switch_tab('import')
                MDButtonText:
                    text: '导入'

            MDButton:
                style: 'filled' if app.current_tab == 'analysis' else 'outlined'
                on_release: app.switch_tab('analysis')
                MDButtonText:
                    text: '分析'

            MDButton:
                style: 'filled' if app.current_tab == 'results' else 'outlined'
                on_release: app.switch_tab('results')
                MDButtonText:
                    text: '结果'

            MDButton:
                style: 'filled' if app.current_tab == 'settings' else 'outlined'
                on_release: app.switch_tab('settings')
                MDButtonText:
                    text: '设置'

        # === 内容区 ===
        MDScrollView:
            MDBoxLayout:
                id: content_box
                orientation: 'vertical'
                spacing: '12dp'
                adaptive_height: True
'''


class RootScreen(MDScreen):
    pass


class StoryOutlineApp(MDApp):
    current_tab = StringProperty('import')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chapters: list[dict] = []
        self._text: str = ''
        self._api_key: str = ''
        self._section_size: int = 50
        self._pipeline: AnalysisPipeline = None
        self._manager: ResultManager = None
        self._thread: threading.Thread = None
        self._running = False
        self._paused = False
        self._settings_file = os.path.join(get_data_dir(), 'settings.json')
        self._step1_results: list[dict] = []
        self._step2_results: list[dict] = []
        self._character: str = ''
        self._style: str = ''
        self._advice: str = ''
        self._storyline: str = ''

    def build(self):
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'
        return Builder.load_string(KV)

    def on_start(self):
        self._load_settings()
        Clock.schedule_once(lambda dt: self.switch_tab('import'))

    @mainthread
    def switch_tab(self, tab: str):
        self.current_tab = tab
        if not self.root:
            Clock.schedule_once(lambda dt: self.switch_tab(tab), 0.1)
            return
        box = self.root.ids.content_box
        box.clear_widgets()
        getattr(self, f'_build_{tab}', self._build_import)()

    # ================================================================
    # 导入
    # ================================================================

    def _build_import(self):
        box = self.root.ids.content_box

        box.add_widget(MDLabel(text='导入文章', font_style='Title', theme_text_color='Primary', adaptive_height=True))
        box.add_widget(MDLabel(text='支持 TXT / DOCX / PDF / EPUB', font_style='Body', theme_text_color='Hint', adaptive_height=True))

        btn = MDButton(MDButtonText(text='选择文件'), style='filled', on_release=self._pick_file)
        btn.pos_hint = {'center_x': 0.5}
        box.add_widget(btn)

        self._lbl_file = MDLabel(text='尚未选择文件', font_style='Body', theme_text_color='Hint', adaptive_height=True)
        box.add_widget(self._lbl_file)
        self._lbl_chapter = MDLabel(text='', font_style='Body', theme_text_color='Hint', adaptive_height=True)
        box.add_widget(self._lbl_chapter)

        btn2 = MDButton(MDButtonText(text='开始分析'), style='filled', on_release=self._start_analysis)
        btn2.pos_hint = {'center_x': 0.5}
        btn2.disabled = True
        self._btn_analyze = btn2
        box.add_widget(btn2)

    # ================================================================
    # 分析
    # ================================================================

    def _build_analysis(self):
        box = self.root.ids.content_box

        self._lbl_progress = MDLabel(text='就绪', font_style='Title', theme_text_color='Primary', adaptive_height=True)
        box.add_widget(self._lbl_progress)

        bar = MDLinearProgressIndicator(value=0)
        self._progress_bar = bar
        box.add_widget(bar)

        self._lbl_detail = MDLabel(text='0/0 章', font_style='Body', theme_text_color='Hint', adaptive_height=True)
        box.add_widget(self._lbl_detail)

        self._log_box = MDBoxLayout(orientation='vertical', spacing='4dp', adaptive_height=True)
        box.add_widget(self._log_box)

        row = MDBoxLayout(spacing='8dp', adaptive_height=True)
        btn_pause = MDButton(MDButtonText(text='暂停'), style='filled', on_release=self._toggle_pause)
        btn_pause.disabled = True
        self._btn_pause = btn_pause
        row.addWidget(btn_pause)
        btn_results = MDButton(MDButtonText(text='查看结果 »'), style='outlined', on_release=lambda _: self.switch_tab('results'))
        row.addWidget(btn_results)
        box.add_widget(row)

        # 恢复之前的日志
        if hasattr(self, '_pending_logs'):
            for log in self._pending_logs:
                self._log_box.add_widget(MDLabel(text=log, font_style='Body', theme_text_color='Hint', adaptive_height=True))

    # ================================================================
    # 结果
    # ================================================================

    def _build_results(self):
        box = self.root.ids.content_box

        sections = [
            ('章节大纲', self._step1_results, lambda r: f"第{r['chapter_index']}章 {r.get('chapter_title','')}\n激励: {r.get('inciting_incident','')[:120]}...\n危机: {r.get('crisis','')[:120]}..."),
            ('阶段总结', self._step2_results, lambda s: f"阶段{s['section_index']} ({s['chapter_range'][0]}-{s['chapter_range'][1]}章): {s.get('summary','')[:200]}..."),
            ('全书故事线', [self._storyline] if self._storyline else [], lambda s: str(s)[:500]),
            ('人物小传', [self._character] if self._character else [], lambda s: str(s)[:500]),
            ('语言风格', [self._style] if self._style else [], lambda s: str(s)[:500]),
            ('写作建议', [self._advice] if self._advice else [], lambda s: str(s)[:500]),
        ]

        has_data = False
        for title, data, fmt in sections:
            if not data:
                continue
            has_data = True
            box.add_widget(MDLabel(text=title, font_style='Title', theme_text_color='Primary', adaptive_height=True))
            for item in data:
                card = MDCard(style='elevated', padding='12dp', radius='8dp', size_hint_y=None, height='auto')
                card.add_widget(MDLabel(text=fmt(item), padding='8dp', adaptive_height=True, font_style='Body', theme_text_color='Secondary'))
                box.add_widget(card)

        if not has_data:
            box.add_widget(MDLabel(text='暂无结果，请先进行分析', font_style='Body', theme_text_color='Hint', adaptive_height=True))

        btn = MDButton(MDButtonText(text='导出 Word'), style='filled', on_release=self._export_docx)
        btn.pos_hint = {'center_x': 0.5}
        box.add_widget(btn)

    # ================================================================
    # 设置
    # ================================================================

    def _build_settings(self):
        box = self.root.ids.content_box

        tf1 = MDTextField(MDTextFieldHintText(text='DeepSeek API Key (sk-...)'), text=self._api_key, password=True, mode='filled')
        self._tf_key = tf1
        box.add_widget(tf1)

        tf2 = MDTextField(MDTextFieldHintText(text='每阶段章节数'), text=str(self._section_size), mode='filled')
        self._tf_section = tf2
        box.add_widget(tf2)

        row = MDBoxLayout(spacing='8dp', adaptive_height=True)
        row.addWidget(MDButton(MDButtonText(text='保存'), style='filled', on_release=self._save_settings))
        row.addWidget(MDButton(MDButtonText(text='测试连接'), style='outlined', on_release=self._test_api))
        box.add_widget(row)

    # ================================================================
    # 文件选择
    # ================================================================

    def _pick_file(self, _):
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup

        def _load(selection):
            popup.dismiss()
            if selection:
                self._load_file(selection[0])

        fc = FileChooserListView(path=get_wenjian_dir(), filters=['*.txt', '*.docx', '*.pdf', '*.epub'])
        fc.bind(on_submit=_load)
        popup = Popup(title='选择文件', content=fc, size_hint=(0.9, 0.8))
        popup.open()

    @mainthread
    def _load_file(self, path: str):
        try:
            self._text = parse_file(path)
            split = split_chapters(self._text)
            self._chapters = [{'index': ch.index, 'title': ch.title, 'content': ch.content, 'status': 'pending'}
                            for ch in split.chapters]
            if self._lbl_file:
                self._lbl_file.text = f'已加载: {os.path.basename(path)}'
                self._lbl_chapter.text = f'{len(self._chapters)} 章 | {len(self._text):,} 字'
            if self._btn_analyze:
                self._btn_analyze.disabled = False
        except Exception as e:
            MDSnackbar(MDSnackbarText(text=f'解析失败: {e}'), y='24dp', pos_hint={'center_x': 0.5}, size_hint_x=0.9).open()

    # ================================================================
    # 分析控制
    # ================================================================

    def _start_analysis(self, _):
        if not self._chapters or not self._api_key:
            MDSnackbar(MDSnackbarText(text='请先导入文件并配置 API Key'), y='24dp', pos_hint={'center_x': 0.5}, size_hint_x=0.9).open()
            return

        self._running = True
        self._paused = False
        self._step1_results = []
        self._step2_results = []
        self._character = ''
        self._style = ''
        self._advice = ''
        self._storyline = ''

        project_dir = os.path.join(get_wenjian_dir(), 'android_project.storyoutline')
        self._manager = ResultManager(project_dir)
        state = ProjectState(
            name='android_project', source_file='', chapters=self._chapters,
            section_size=self._section_size,
        )
        client = DeepSeekClient(api_key=self._api_key)
        self._pipeline = AnalysisPipeline(client=client, manager=self._manager, state=state, section_size=state.section_size)

        self._pipeline.on_progress = lambda msg: Clock.schedule_once(lambda dt: self._on_progress(msg))
        self._pipeline.on_chapter_done = lambda idx, r: Clock.schedule_once(lambda dt: self._on_chapter(idx, r))
        self._pipeline.on_section_done = lambda idx, e: Clock.schedule_once(lambda dt: self._on_section(e))
        self._pipeline.on_character_done = lambda t: Clock.schedule_once(lambda dt: self._on_character(t))
        self._pipeline.on_style_done = lambda t: Clock.schedule_once(lambda dt: self._on_style(t))
        self._pipeline.on_writing_advice_done = lambda t: Clock.schedule_once(lambda dt: self._on_advice(t))
        self._pipeline.on_storyline_done = lambda r: Clock.schedule_once(lambda dt: self._on_storyline(r))
        self._pipeline.on_all_done = lambda: Clock.schedule_once(lambda dt: self._on_done())
        self._pipeline.on_error = lambda idx, err: Clock.schedule_once(lambda dt: self._snack(f'第{idx}章错误: {err}'))

        self._pending_logs = ['开始分析...']
        self.switch_tab('analysis')
        if hasattr(self, '_btn_pause') and self._btn_pause:
            self._btn_pause.disabled = False

        self._thread = threading.Thread(target=self._pipeline.run, daemon=True)
        self._thread.start()

    def _toggle_pause(self, _):
        if not self._pipeline:
            return
        btn = self._btn_pause
        if self._paused:
            self._pipeline.resume()
            self._paused = False
            if btn: btn.children[0].text = '暂停'
        else:
            self._pipeline.pause()
            self._paused = True
            if btn: btn.children[0].text = '继续'

    @mainthread
    def _on_progress(self, msg: str):
        if hasattr(self, '_lbl_progress'):
            self._lbl_progress.text = msg
        self._add_log(msg)

    @mainthread
    def _on_chapter(self, idx: int, result: dict):
        self._step1_results.append(result)
        total = len(self._chapters)
        if hasattr(self, '_progress_bar'):
            self._progress_bar.value = idx * 100 / total
        if hasattr(self, '_lbl_detail'):
            self._lbl_detail.text = f'{idx}/{total} 章'
        self._add_log(f'✅ 第{idx}章完成: {result.get("chapter_title", "")}')

    @mainthread
    def _on_section(self, entry: dict):
        self._step2_results.append(entry)
        self._add_log(f'📊 阶段总结完成 ({entry["chapter_range"][0]}-{entry["chapter_range"][1]}章)')

    @mainthread
    def _on_character(self, text: str):
        self._character = text
        self._add_log('👤 人物分析完成')

    @mainthread
    def _on_style(self, text: str):
        self._style = text
        self._add_log('🎨 风格分析完成')

    @mainthread
    def _on_advice(self, text: str):
        self._advice = text
        self._add_log('✍️ 写作建议完成')

    @mainthread
    def _on_storyline(self, result: dict):
        self._storyline = result.get('overall_storyline', '')
        self._add_log('📈 全书故事线完成')

    @mainthread
    def _on_done(self):
        self._running = False
        if hasattr(self, '_progress_bar'):
            self._progress_bar.value = 100
        if hasattr(self, '_lbl_progress'):
            self._lbl_progress.text = '全部完成！'
        if hasattr(self, '_btn_pause'):
            self._btn_pause.disabled = True
        self._snack('分析完成！可查看结果或导出')

    def _add_log(self, msg: str):
        if hasattr(self, '_pending_logs'):
            self._pending_logs.append(msg)
        if hasattr(self, '_log_box') and self._log_box:
            self._log_box.add_widget(MDLabel(text=msg, font_style='Body', theme_text_color='Hint', adaptive_height=True))

    # ================================================================
    # 导出
    # ================================================================

    def _export_docx(self, _):
        if not self._manager:
            self._snack('暂无数据可导出')
            return
        try:
            path = os.path.join(get_wenjian_dir(), 'storyoutline_结果.docx')
            self._manager.export_to_docx(path, 'StoryOutline分析结果')
            self._snack(f'已导出: {path}')
        except Exception as e:
            self._snack(f'导出失败: {e}')

    # ================================================================
    # 设置
    # ================================================================

    def _load_settings(self):
        try:
            if os.path.exists(self._settings_file):
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._api_key = data.get('api_key', '')
                self._section_size = int(data.get('section_size', 50))
        except Exception:
            pass

    def _save_settings(self, _):
        try:
            self._api_key = getattr(self._tf_key, 'text', self._api_key)
            self._section_size = int(getattr(self._tf_section, 'text', '50') or '50')
        except Exception:
            pass
        try:
            os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump({'api_key': self._api_key, 'section_size': self._section_size}, f)
            self._snack('设置已保存')
        except Exception as e:
            self._snack(f'保存失败: {e}')

    def _test_api(self, _):
        key = getattr(self._tf_key, 'text', self._api_key)
        if not key:
            self._snack('请输入 API Key')
            return
        def _test():
            import requests
            try:
                resp = requests.post('https://api.deepseek.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                    json={'model': 'deepseek-chat', 'messages': [{'role': 'user', 'content': 'OK'}], 'max_tokens': 10},
                    timeout=15)
                if resp.status_code == 200:
                    Clock.schedule_once(lambda dt: self._snack('连接成功！'))
                else:
                    Clock.schedule_once(lambda dt: self._snack(f'错误: {resp.status_code}'))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._snack(f'连接失败: {e}'))
        threading.Thread(target=_test, daemon=True).start()

    def _snack(self, msg: str):
        MDSnackbar(MDSnackbarText(text=msg), y='24dp', pos_hint={'center_x': 0.5}, size_hint_x=0.9).open()


if __name__ == '__main__':
    StoryOutlineApp().run()
