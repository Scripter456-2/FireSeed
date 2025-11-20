#!/usr/bin/env python3
"""
FireSeed6 — a PyQt5 Chromium-based mini-browser.
Features: tabs, homepage, bookmarks (add/delete), session restore, dev console, downloads, user CSS.
Requires: PyQt5, PyQtWebEngine
"""

import sys
import os
import json
import typing
from pathlib import Path
from urllib.parse import urlparse, quote_plus

from PyQt5.QtCore import QUrl, Qt, QSize, QStandardPaths, QFileInfo
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QAction, QTabWidget, QWidget,
    QVBoxLayout, QTextEdit, QDockWidget, QPushButton, QLabel, QHBoxLayout,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog, QMenu, QDialog
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEngineScript, QWebEngineDownloadItem
)

# ---------- Configuration / Storage ----------
APP_NAME = "FireSeed6"
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"
SESSION_FILE = DATA_DIR / "session.json"
USERCSS_FILE = DATA_DIR / "userstyle.css"

DEFAULT_USER_CSS = """
:root { color-scheme: dark; }
html, body { background-color: #0b0f14 !important; color: #d7dade !important; }
img { max-width: 100%; height: auto; }
"""

HOMEPAGE_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>FireSeed6</title>
<style>
body{margin:0;font-family:Arial;background:#07101a;color:#d7dade;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh}
a{color:#7bdff6;text-decoration:none;padding:8px 12px;border-radius:8px;background:#071a22;margin:6px;display:inline-block}
input{padding:12px;border-radius:24px;border:1px solid #203139;width:360px;background:#02121a;color:#cfe7ee}
.links{margin-top:18px}
footer{position:fixed;bottom:6px;color:#6b7d83;font-size:12px}
</style>
</head>
<body>
<h1 style="font-weight:300">FireSeed6</h1>
<input id="q" placeholder="Search or enter URL" onkeypress="if(event.key==='Enter'){location.href='https://www.google.com/search?q='+encodeURIComponent(this.value)}">
<div class="links">
<a href="https://www.youtube.com">YouTube</a>
<a href="https://www.google.com">Google</a>
<a href="https://github.com">GitHub</a>
</div>
<footer>© FireSeed6</footer>
</body>
</html>
"""

# ---------- JSON helpers ----------
def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return default

def save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

# ---------- Utilities ----------
def make_safe_js_string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)

def ensure_http_like(txt: str) -> str:
    txt = txt.strip()
    if not txt:
        return txt
    if txt.startswith(("http://", "https://", "file://")):
        return txt
    if " " not in txt and "." in txt and not txt.endswith("."):
        return "https://" + txt
    return "https://www.google.com/search?q=" + quote_plus(txt)

# ---------- User CSS injection (compatible) ----------
def install_user_css(profile: QWebEngineProfile, css: str, name: str = "fireseed_user_css"):
    scripts = profile.scripts()
    # remove existing script with same name — compatible with PyQt versions
    try:
        names = list(scripts.scriptNames())
    except Exception:
        # fallback: older API may not have scriptNames; try findScripts with a name pattern not supported -> ignore
        names = []
    for s_name in names:
        try:
            if s_name == name:
                found = scripts.findScript(s_name)
                if found:
                    scripts.remove(found)
        except Exception:
            pass
    # build JS to inject CSS safely
    js = f"""
(function(){{
  try {{
    var css = {make_safe_js_string(css)};
    var id = 'fireseed6-usercss';
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    var style = document.createElement('style');
    style.id = id;
    style.type = 'text/css';
    style.appendChild(document.createTextNode(css));
    (document.head || document.documentElement).appendChild(style);
  }} catch(e) {{ console.error('usercss inject', e); }}
}})();
"""
    script = QWebEngineScript()
    script.setName(name)
    script.setSourceCode(js)
    script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    script.setRunsOnSubFrames(True)
    # Some PyQt builds require MainWorld constant as int; MainWorld attribute exists normally
    try:
        script.setWorldId(QWebEngineScript.MainWorld)
    except Exception:
        pass
    try:
        scripts.insert(script)
    except Exception:
        try:
            QWebEngineProfile.defaultProfile().scripts().insert(script)
        except Exception:
            pass

# Helper: install CSS from userdata file if exists (called per profile)
def install_user_css_from_file(profile: QWebEngineProfile):
    css = DEFAULT_USER_CSS
    try:
        if Path(USERCSS_FILE).exists():
            css = Path(USERCSS_FILE).read_text(encoding='utf-8')
    except Exception:
        pass
    install_user_css(profile, css, name="fireseed_user_css")

# ---------- Browser Tab ----------
class BrowserTab(QWidget):
    def __init__(self, url='about:home'):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.web = QWebEngineView()
        self.layout.addWidget(self.web)
        self.setLayout(self.layout)
        # ensure Accept-Language
        try:
            self.web.page().profile().setHttpAcceptLanguage('en-US,en;q=0.9')
        except Exception:
            pass
        # inject user css for this profile
        try:
            install_user_css_from_file(self.web.page().profile())
        except Exception:
            pass
        self.load_url(url)

    def load_url(self, url):
        if url == 'about:home':
            self.web.setHtml(HOMEPAGE_HTML, QUrl('about:home'))
        else:
            self.web.load(QUrl(url))

# ---------- Main App ----------
class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 820)

        # storage
        self.bookmarks = load_json(BOOKMARKS_FILE, [])
        self.session = load_json(SESSION_FILE, {})
        self.history = []

        self._build_ui()
        self._restore_session()

    def _build_ui(self):
        # tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        # navigation toolbar
        nav = QToolBar('Navigation')
        nav.setIconSize(QSize(18,18))
        self.addToolBar(nav)

        self.back_act = QAction('◀', self)
        self.forward_act = QAction('▶', self)
        self.reload_act = QAction('⟳', self)
        self.home_act = QAction('🏠', self)
        self.newtab_act = QAction('+', self)

        self.addr = QLineEdit(self)
        self.addr.returnPressed.connect(self._on_enter_address)
        self.addr.setPlaceholderText("Search or enter address...")

        nav.addAction(self.back_act)
        nav.addAction(self.forward_act)
        nav.addAction(self.reload_act)
        nav.addAction(self.home_act)
        nav.addAction(self.newtab_act)
        nav.addWidget(self.addr)

        self.back_act.triggered.connect(lambda: self.current_tab().web.back())
        self.forward_act.triggered.connect(lambda: self.current_tab().web.forward())
        self.reload_act.triggered.connect(lambda: self.current_tab().web.reload())
        self.home_act.triggered.connect(lambda: self.current_tab().load_url('about:home'))
        self.newtab_act.triggered.connect(lambda: self._add_tab('about:home'))

        # bookmarks toolbar
        self.bookmarks_toolbar = QToolBar("Bookmarks")
        self.addToolBar(Qt.TopToolBarArea, self.bookmarks_toolbar)
        self.bookmarks_toolbar.setMovable(False)
        self._refresh_bookmarks_toolbar()

        # menu: minimal (no settings, no adblock, no extensions)
        self.menuBar().addAction("Bookmarks").triggered.connect(lambda: self.manage_bookmarks())
        self.dev_action = QAction("<> Dev", self)
        self.dev_action.triggered.connect(self.toggle_console)
        self.menuBar().addAction(self.dev_action)

        # console dock
        self._build_console()

        # downloads panel
        self.downloads_dock = QDockWidget("Downloads", self)
        self.downloads_list = QListWidget()
        self.downloads_dock.setWidget(self.downloads_list)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.downloads_dock)
        self.downloads_dock.setVisible(False)

        # initial tab
        self._add_tab('about:home')

    def _build_console(self):
        self.console = QDockWidget("Dev Console", self)
        self.console.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        console_widget = QWidget()
        vb = QVBoxLayout(console_widget)

        label = QLabel("Run JavaScript (current tab):")
        self.js_edit = QTextEdit()
        run_js_btn = QPushButton("Run JS")
        run_js_btn.clicked.connect(self.run_js)

        label_css = QLabel("Inject CSS (saved to userstyle.css):")
        self.css_edit = QTextEdit()
        # prefill with existing CSS file if exists
        try:
            if Path(USERCSS_FILE).exists():
                self.css_edit.setPlainText(Path(USERCSS_FILE).read_text(encoding='utf-8'))
            else:
                self.css_edit.setPlainText(DEFAULT_USER_CSS)
        except Exception:
            self.css_edit.setPlainText(DEFAULT_USER_CSS)
        inject_css_btn = QPushButton("Save & Inject CSS")
        inject_css_btn.clicked.connect(self.save_and_inject_css)

        btn_row = QHBoxLayout()
        btn_row.addWidget(run_js_btn)
        btn_row.addWidget(inject_css_btn)

        vb.addWidget(label)
        vb.addWidget(self.js_edit)
        vb.addLayout(btn_row)
        vb.addWidget(label_css)
        vb.addWidget(self.css_edit)

        self.console.setWidget(console_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console)
        self.console.setVisible(False)

    def save_and_inject_css(self):
        try:
            Path(USERCSS_FILE).write_text(self.css_edit.toPlainText(), encoding='utf-8')
            # re-install into default profile and all active tab profiles
            try:
                install_user_css(QWebEngineProfile.defaultProfile(), self.css_edit.toPlainText(), name="fireseed_user_css")
            except Exception:
                pass
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                try:
                    install_user_css(t.web.page().profile(), self.css_edit.toPlainText(), name="fireseed_user_css")
                    t.web.reload()
                except Exception:
                    pass
        except Exception:
            QMessageBox.warning(self, "CSS Save", "Failed to save or inject CSS.")

    def run_js(self):
        js = self.js_edit.toPlainText()
        tab = self.current_tab()
        if tab:
            try:
                tab.web.page().runJavaScript(js)
            except Exception:
                pass

    def toggle_console(self):
        self.console.setVisible(not self.console.isVisible())

    # ---------- tab & UI helpers ----------
    def _add_tab(self, url='about:home'):
        tab = BrowserTab(url)
        idx = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(idx)

        page = tab.web.page()
        page.urlChanged.connect(lambda qurl, t=tab: self._on_url_changed(t, qurl))
        page.loadFinished.connect(lambda ok, t=tab: self._on_load_finished(t, ok))
        try:
            page.profile().downloadRequested.connect(self._on_download_requested)
        except Exception:
            pass

        return tab

    def _close_tab(self, idx):
        if self.tabs.count() > 1:
            self.tabs.removeTab(idx)
        else:
            self.close()

    def current_tab(self) -> typing.Optional[BrowserTab]:
        return self.tabs.currentWidget()

    def _on_tab_changed(self, idx):
        tab = self.current_tab()
        if not tab:
            return
        url = tab.web.url().toString()
        self.addr.setText(url or "")
        try:
            self.back_act.setEnabled(tab.web.history().canGoBack())
            self.forward_act.setEnabled(tab.web.history().canGoForward())
        except Exception:
            pass

    def _on_url_changed(self, tab: BrowserTab, qurl: QUrl):
        if self.tabs.indexOf(tab) == self.tabs.currentIndex():
            self.addr.setText(qurl.toString())

    def _on_load_finished(self, tab: BrowserTab, ok: bool):
        url = tab.web.url().toString()
        title = tab.web.title() or url
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            display = title if len(title) <= 30 else title[:27] + "..."
            self.tabs.setTabText(idx, display)
        self.history.append({"title": title, "url": url})

    def update_tab_title_from_tab(self, tab: BrowserTab, title: str):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            display = title if len(title) <= 30 else title[:27] + "..."
            self.tabs.setTabText(idx, display)
            if idx == self.tabs.currentIndex():
                self.addr.setText(tab.web.url().toString())

    def update_tab_favicon(self, tab: BrowserTab, icon):
        idx = self.tabs.indexOf(tab)
        if idx >= 0 and not icon.isNull():
            self.tabs.setTabIcon(idx, icon)

    def _on_enter_address(self):
        txt = self.addr.text().strip()
        if not txt:
            return
        target = ensure_http_like(txt)
        self.current_tab().load_url(target)

    # ---------- bookmarks ----------
    def _refresh_bookmarks_toolbar(self):
        self.bookmarks_toolbar.clear()
        for bm in self.bookmarks:
            act = QAction(bm.get("title", bm.get("url")), self)
            act.setToolTip(bm.get("url"))
            act.triggered.connect(lambda checked=False, u=bm.get("url"): self.current_tab().load_url(u))
            self.bookmarks_toolbar.addAction(act)
        manage = QAction("★", self)
        manage.triggered.connect(self.manage_bookmarks)
        self.bookmarks_toolbar.addAction(manage)

    def manage_bookmarks(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Bookmarks Manager")
        dlg.resize(420, 320)
        layout = QVBoxLayout(dlg)

        list_widget = QListWidget()
        for bm in self.bookmarks:
            item = QListWidgetItem(f"{bm.get('title', bm.get('url'))} — {bm.get('url')}")
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Current")
        delete_btn = QPushButton("Delete Selected")
        close_btn = QPushButton("Close")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        add_btn.clicked.connect(lambda: self._add_current_bookmark(list_widget))
        delete_btn.clicked.connect(lambda: self._delete_selected_bookmark(list_widget))
        close_btn.clicked.connect(dlg.accept)

        dlg.exec_()

    def _add_current_bookmark(self, list_widget):
        tab = self.current_tab()
        if tab:
            url = tab.web.url().toString()
            title = tab.web.title() or url
            self.bookmarks.append({"title": title, "url": url})
            save_json(BOOKMARKS_FILE, self.bookmarks)
            self._refresh_bookmarks_toolbar()
            list_widget.addItem(f"{title} — {url}")

    def _delete_selected_bookmark(self, list_widget):
        selected = list_widget.currentRow()
        if selected >= 0:
            del self.bookmarks[selected]
            save_json(BOOKMARKS_FILE, self.bookmarks)
            list_widget.takeItem(selected)
            self._refresh_bookmarks_toolbar()

    # ---------- CSS / Dev ----------
    def inject_css(self):
        css = self.css_edit.toPlainText()
        try:
            install_user_css(QWebEngineProfile.defaultProfile(), css, name="user_css_dynamic")
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                try:
                    install_user_css(t.web.page().profile(), css, name="user_css_dynamic")
                    t.web.reload()
                except Exception:
                    pass
        except Exception:
            pass

    # ---------- downloads ----------
    def _on_download_requested(self, download: QWebEngineDownloadItem):
        suggested = QFileDialog.getSaveFileName(self, "Save File", download.path() or download.downloadFileName())[0]
        if not suggested:
            download.cancel()
            return
        download.setPath(suggested)
        download.accept()
        item = QListWidgetItem(f"Downloading: {QFileInfo(suggested).fileName()}")
        self.downloads_list.addItem(item)
        self.downloads_dock.setVisible(True)
        download.finished.connect(lambda: item.setText(f"Completed: {QFileInfo(suggested).fileName()}"))

    def save_link_from_context(self, page):
        url = page.contextMenuData().linkUrl().toString()
        if not url:
            QMessageBox.information(self, "No link", "No link available under cursor.")
            return
        suggested = QFileDialog.getSaveFileName(self, "Save Link As", os.path.basename(urlparse(url).path) or "download")[0]
        if not suggested:
            return
        profile = page.profile()
        d = profile.download(url, suggested)
        d.accept()

    # ---------- session persistence ----------
    def _restore_session(self):
        saved = load_json(SESSION_FILE, {})
        tabs = saved.get("tabs", [])
        if tabs:
            try:
                while self.tabs.count():
                    self.tabs.removeTab(0)
            except Exception:
                pass
            for turl in tabs:
                self._add_tab(turl)
        else:
            pass

    def closeEvent(self, event):
        tabs = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            u = tab.web.url().toString()
            tabs.append(u or "about:home")
        save_json(SESSION_FILE, {"tabs": tabs})
        save_json(BOOKMARKS_FILE, self.bookmarks)
        super().closeEvent(event)

# ---------- Entry point ----------
def main():
    app = QApplication(sys.argv)
    try:
        _ = QWebEngineProfile()
    except Exception:
        QMessageBox.critical(None, "Missing components", "PyQtWebEngine may not be installed.\nInstall with:\n\npip install PyQt5 PyQtWebEngine")
        return
    w = BrowserApp()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
