# -*- coding: utf-8 -*-
"""StoryOutline - Self-contained Android APK entry."""
import os, sys, json, threading, time, re
from dataclasses import dataclass, field

def parse_file(path):
    import chardet
    with open(path, "rb") as f: raw = f.read(100*1024)
    enc = chardet.detect(raw).get("encoding", "utf-8") or "utf-8"
    if enc.lower().startswith("gb"): enc = "gbk"
    with open(path, "r", encoding=enc, errors="replace") as f: return f.read()

@dataclass
class ChapterInfo: index: int; title: str; content: str; start_pos: int = 0
@dataclass
class SplitResult: chapters: list = field(default_factory=list); total_chapters: int = 0; total_chars: int = 0; pattern_used: str = ""

def split_chapters(text, custom_patterns=None):
    patterns = [
        r"^\s*第[一-鿿百千万零]+[章节回卷]",
        r"^\s*第\s*[0-9]+\s*[章节回卷]",
        r"^\s*[Cc]hapter\s+[0-9]+",
    ]
    if custom_patterns: patterns = custom_patterns + patterns
    regex = re.compile("|".join("(?:" + p + ")" for p in patterns), re.MULTILINE)
    matches = list(regex.finditer(text))
    if not matches:
        return SplitResult(chapters=[ChapterInfo(index=1, title="全文", content=text.strip())], total_chapters=1, total_chars=len(text))
    chs = []
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        chs.append(ChapterInfo(index=i+1, title=m.group().strip(), content=text[m.end():end].strip()))
    return SplitResult(chapters=chs, total_chapters=len(chs), total_chars=len(text), pattern_used=",".join(patterns[:2]))

class DeepSeekClient:
    def __init__(self, api_key="", model="deepseek-chat", timeout=120, max_tokens=4096, temperature=0.7):
        self.api_key = api_key; self.model = model; self.timeout = timeout; self.max_tokens = max_tokens; self.temperature = temperature
    def _call(self, msgs):
        import requests as _r
        for i in range(4):
            try:
                resp = _r.post("https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
                    json={"model": self.model, "messages": msgs, "max_tokens": self.max_tokens, "temperature": self.temperature}, timeout=self.timeout)
                return resp.json()["choices"][0]["message"]["content"].strip()
            except: time.sleep(5*(i+1) if i < 3 else 0)
        raise RuntimeError("API request failed")
    def analyze_chapter(self, title, content):
        return self._call([{"role":"system","content":"You are a professional story analyst. Output in Chinese: 1.激励事件 2.进展纠葛 3.危机 4.高潮 5.结局. 2-4 sentences each."},{"role":"user","content":title+"

"+content}])
    def summarize_section(self, outlines):
        return self._call([{"role":"system","content":"Summarize chapter outlines in Chinese."},{"role":"user","content":str(outlines)[:8000]}])
    def generate_storyline(self, total, summaries):
        return self._call([{"role":"system","content":"Analyze overall story arc in Chinese."},{"role":"user","content":str(summaries)[:8000]}])
    def analyze_characters(self, outlines, count):
        return self._call([{"role":"system","content":"Extract main characters in Chinese."},{"role":"user","content":str(outlines)[:8000]}])
    def analyze_writing_style(self, outlines, count, samples):
        return self._call([{"role":"system","content":"Analyze writing style in Chinese."},{"role":"user","content":samples[:8000]}])
    def analyze_writing_advice(self, count, samples):
        return self._call([{"role":"system","content":"Provide writing advice with quoted passages in Chinese."},{"role":"user","content":samples[:8000]}])

class ProjectState:
    def __init__(self, name="", source_file="", chapters=None, section_size=50):
        self.name = name; self.source_file = source_file; self.chapters = chapters or []
        self.step1_results = []; self.step2_results = []; self.step3_result = None
        self.character_analysis = ""; self.writing_style = ""; self.writing_advice = ""
        self.current_stage = ""; self.analyzed_count = 0; self.section_size = section_size

class ResultManager:
    def __init__(self, project_dir):
        self.project_dir = project_dir; os.makedirs(project_dir, exist_ok=True)
    def _fp(self, f): return os.path.join(self.project_dir, f)
    def _w(self, f, d):
        with open(self._fp(f), "w", encoding="utf-8") as fp: json.dump(d, fp, ensure_ascii=False)
    def _r(self, f):
        p = self._fp(f)
        return json.load(open(p, "r", encoding="utf-8")) if os.path.isfile(p) else None
    def save_state(self, s): self._w("project.json", {"name":s.name,"source_file":s.source_file,"chapters":s.chapters,"current_stage":s.current_stage,"analyzed_count":s.analyzed_count,"section_size":s.section_size})
    def load_state(self):
        d = self._r("project.json")
        if not d: return ProjectState()
        return ProjectState(name=d.get("name",""), source_file=d.get("source_file",""), chapters=d.get("chapters",[]), section_size=d.get("section_size",50))
    def save_step1_results(self, r): self._w("step1_results.json", r)
    def load_step1_results(self): return self._r("step1_results.json") or []
    def save_step2_results(self, r): self._w("step2_results.json", r)
    def load_step2_results(self): return self._r("step2_results.json") or []
    def save_step3_result(self, r): self._w("step3_result.json", r)
    def load_step3_result(self): return self._r("step3_result.json")
    def _read_json(self, f): return self._r(f)
    def _write_json(self, f, d): self._w(f, d)
    def export_to_docx(self, path, name): pass

class AnalysisPipeline:
    def __init__(self, client=None, manager=None, state=None, section_size=50):
        self.client = client; self.manager = manager; self.state = state; self.section_size = section_size
        self.on_progress = lambda m: None; self.on_chapter_done = lambda i, r: None
        self.on_section_done = lambda i, e: None; self.on_character_done = lambda t: None
        self.on_style_done = lambda t: None; self.on_writing_advice_done = lambda t: None
        self.on_storyline_done = lambda r: None; self.on_all_done = lambda: None
        self.on_error = lambda i, e: None; self._paused = self._stopped = False
        self._text_samples = []; self._step1 = []; self._step2 = []
    def pause(self): self._paused = True
    def resume(self): self._paused = False
    def stop(self): self._stopped = True
    def run(self):
        chapters = self.state.chapters; total = len(chapters)
        for i, ch in enumerate(chapters):
            if self._stopped: return
            while self._paused: time.sleep(0.5)
            try:
                text = self.client.analyze_chapter(ch.get("title",""), ch.get("content",""))
                result = {"chapter_index": i+1, "chapter_title": ch.get("title",""), "inciting_incident":"", "progressive_complications":"", "crisis":"", "climax":"", "resolution":"", "raw":text}
                for kw, key in [("激励事件","inciting_incident"),("进展纠葛","progressive_complications"),("危机","crisis"),("高潮","climax"),("结局","resolution")]:
                    idx = text.find(kw)
                    if idx >= 0:
                        rest = text[idx+len(kw):].lstrip("：: 
")
                        parts = rest.split("
")
                        result[key] = parts[0][:300] if parts else rest[:300]
                self._step1.append(result); ch["status"] = "done"
                self._text_samples.append(ch.get("content","")[:200])
                self.state.step1_results = self._step1; self.state.analyzed_count = len(self._step1)
                self.on_chapter_done(i+1, result)
            except Exception as e: self.on_error(i+1, str(e))
            time.sleep(0.5)
        if self._step1:
            try:
                summary = self.client.summarize_section(self._step1)
                self._step2.append({"section_index":1,"chapter_range":[1,total],"summary":summary})
                self.on_section_done(1, self._step2[-1])
            except: pass
            if total >= 20:
                try: self.on_character_done(self.client.analyze_characters(self._step1, total))
                except: pass
            try:
                storyline = self.client.generate_storyline(total, self._step2)
                self.state.step3_result = {"total_chapters":total,"overall_storyline":storyline}
                self.on_storyline_done(self.state.step3_result)
            except: pass
            try: self.on_style_done(self.client.analyze_writing_style(self._step1, total, "
".join(self._text_samples)))
            except: pass
            try: self.on_writing_advice_done(self.client.analyze_writing_advice(total, "
".join(self._text_samples)))
            except: pass
        self.on_all_done()

def get_data_dir():
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "StoryOutline")
    os.makedirs(d, exist_ok=True); return d

def get_wenjian_dir():
    d = os.path.join(get_data_dir(), "wenjian")
    os.makedirs(d, exist_ok=True); return d

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

# from src.file_parser import parse_file
# from src.chapter_splitter import split_chapters
# from src.deepseek_client import DeepSeekClient
# from src.analysis_pipeline import AnalysisPipeline
# from src.result_manager import ProjectState, ResultManager
# from src.utils import get_wenjian_dir, get_data_dir


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
