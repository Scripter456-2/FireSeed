#!/usr/bin/env python3
"""
FireSeed5 — a PyQt5 Chromium-based mini-browser with saving, bookmarks, and homepage.
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
APP_NAME = "FireSeed5"
DATA_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"
SESSION_FILE = DATA_DIR / "session.json"

DEFAULT_USER_CSS = """
:root { color-scheme: dark; }
html, body { background-color: #0b0f14 !important; color: #d7dade !important; }
img { max-width: 100%; height: auto; }
"""

HOMEPAGE_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>FireSeed5</title>
<style>body{margin:0;font-family:Arial;background:#07101a;color:#d7dade;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh}
a{color:#7bdff6;text-decoration:none;padding:8px 12px;border-radius:8px;background:#071a22;margin:6px;display:inline-block}
input{padding:12px;border-radius:24px;border:1px solid #203139;width:360px;background:#02121a;color:#cfe7ee}
footer{position:fixed;bottom:6px;color:#6b7d83;font-size:12px}
</style></head><body>
<h1 style="font-weight:300">FireSeed5</h1>
<input id="q" placeholder="Search or enter URL" onkeypress="if(event.key==='Enter'){location.href='https://www.google.com/search?q='+encodeURIComponent(this.value)}">
<div style="margin-top:18px">
<a href="https://www.youtube.com">YouTube</a><a href="https://www.google.com">Google</a><a href="https://github.com">GitHub</a>
</div><footer>© FireSeed5</footer></body></html>
"""

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

# ---------- User CSS injection ----------
def install_user_css(profile: QWebEngineProfile, css: str, name: str = "fireseed_user_css"):
    scripts = profile.scripts()
    for s in list(scripts.findScripts()):
        try:
            if s.name() == name:
                scripts.remove(s)
        except Exception:
            pass
    js = f"""
(function(){{
  try {{
    var css = {make_safe_js_string(css)};
    var id = 'fireseed5-usercss';
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
    script.setWorldId(QWebEngineScript.MainWorld)
    try:
        scripts.insert(script)
    except Exception:
        QWebEngineProfile.defaultProfile().scripts().insert(script)

# ---------- Browser Tab ----------
class BrowserTab(QWidget):
    def __init__(self, url='about:home', user_css=DEFAULT_USER_CSS):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.web = QWebEngineView()
        self.layout.addWidget(self.web)
        self.setLayout(self.layout)
        self._favicon = None

        profile = self.web.page().profile()
        profile.setHttpAcceptLanguage('en-US,en;q=0.9')

        try:
            install_user_css(profile, user_css)
        except Exception:
            try:
                install_user_css(QWebEngineProfile.defaultProfile(), user_css)
            except Exception:
                pass

        self.web.titleChanged.connect(self._on_title_changed)
        self.web.iconChanged.connect(self._on_icon_changed)
        self.web.setContextMenuPolicy(Qt.CustomContextMenu)
        self.web.customContextMenuRequested.connect(self._on_context_menu)

        self.load_url(url)

    def load_url(self, url):
        if url == 'about:home':
            self.web.setHtml(HOMEPAGE_HTML, QUrl('about:home'))
        else:
            self.web.load(QUrl(url))

    def _on_title_changed(self, title):
        w = self.window()
        if hasattr(w, 'update_tab_title_from_tab'):
            w.update_tab_title_from_tab(self, title)

    def _on_icon_changed(self, icon):
        self._favicon = icon
        w = self.window()
        if hasattr(w, 'update_tab_favicon'):
            w.update_tab_favicon(self, icon)

    def _on_context_menu(self, pos):
        page = self.web.page()
        menu = QMenu()
        open_new_tab = QAction("Open link in new tab", self)
        save_link = QAction("Save link as...", self)
        copy_link = QAction("Copy link address", self)
        open_new_tab.triggered.connect(lambda: page.contextMenuData().linkUrl().toString() and self.window()._add_tab(page.contextMenuData().linkUrl().toString()))
        save_link.triggered.connect(lambda: self.window().save_link_from_context(page))
        copy_link.triggered.connect(lambda: QApplication.clipboard().setText(page.contextMenuData().linkUrl().toString()))
        menu.addAction(open_new_tab)
        menu.addAction(save_link)
        menu.addAction(copy_link)
        menu.exec_(self.web.mapToGlobal(pos))

# ---------- Main App ----------
class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 820)

        self.bookmarks = load_json(BOOKMARKS_FILE, [])
        self.session = load_json(SESSION_FILE, {})
        self.history = []

        self._build_ui()
        self._apply_default_css()
        self._restore_session()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        nav = QToolBar("Navigation")
        nav.setIconSize(QSize(18, 18))
        self.addToolBar(nav)

        self.back_act = QAction(QIcon.fromTheme('go-previous'), "Back", self)
        self.forward_act = QAction(QIcon.fromTheme('go-next'), "Forward", self)
        self.reload_act = QAction(QIcon.fromTheme('view-refresh'), "Reload", self)
        self.home_act = QAction(QIcon.fromTheme('go-home'), "Home", self)
        self.newtab_act = QAction(QIcon.fromTheme('tab-new'), "New Tab", self)

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

        self.bookmarks_toolbar = QToolBar("Bookmarks")
        self.addToolBar(Qt.TopToolBarArea, self.bookmarks_toolbar)
        self.bookmarks_toolbar.setMovable(False)
        self._refresh_bookmarks_toolbar()

        self.menuBar().addAction("Bookmarks").triggered.connect(lambda: self.manage_bookmarks())
        self.dev_action = QAction("<> Dev", self)
        self.dev_action.triggered.connect(self.toggle_console)
        self.menuBar().addAction(self.dev_action)

        self._build_console()

        self.downloads_dock = QDockWidget("Downloads", self)
        self.downloads_list = QListWidget()
        self.downloads_dock.setWidget(self.downloads_list)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.downloads_dock)
        self.downloads_dock.setVisible(False)

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

        label_css = QLabel("Inject CSS (applies to all pages):")
        self.css_edit = QTextEdit()
        self.css_edit.setPlainText(DEFAULT_USER_CSS)
        inject_css_btn = QPushButton("Inject CSS")
        inject_css_btn.clicked.connect(self.inject_css)

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

    # ---------- Bookmark Manager ----------
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
        dlg.resize(400, 300)
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

    # ---------- Tabs / CSS / JS ----------
    def _add_tab(self, url='about:home'):
        tab = BrowserTab(url)
        idx = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(idx)

        page = tab.web.page()
        page.urlChanged.connect(lambda qurl, t=tab: self._on_url_changed(t, qurl))
        page.loadFinished.connect(lambda ok, t=tab: self._on_load_finished(t, ok))
        page.profile().downloadRequested.connect(self._on_download_requested)
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
        self.back_act.setEnabled(tab.web.history().canGoBack())
        self.forward_act.setEnabled(tab.web.history().canGoForward())

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

    def _apply_default_css(self):
        try:
            install_user_css(QWebEngineProfile.defaultProfile(), DEFAULT_USER_CSS)
        except Exception:
            pass

    def inject_css(self):
        css = self.css_edit.toPlainText()
        try:
            install_user_css(QWebEngineProfile.defaultProfile(), css, name="user_css_dynamic")
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                t.web.reload()
        except Exception:
            pass

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

    # ---------- Downloads ----------
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

    # ---------- Session ----------
    def _restore_session(self):
        saved = load_json(SESSION_FILE, {})
        tabs = saved.get("tabs", [])
        if tabs:
            while self.tabs.count():
                self.tabs.removeTab(0)
            for turl in tabs:
                self._add_tab(turl)

    def closeEvent(self, event):
        tabs = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            u = tab.web.url().toString()
            tabs.append(u or "about:home")
        save_json(SESSION_FILE, {"tabs": tabs})
        save_json(BOOKMARKS_FILE, self.bookmarks)
        super().closeEvent(event)

# ---------- Entry Point ----------
def main():
    app = QApplication(sys.argv)
    win = BrowserApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
