### File: FireSeed2.py
import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QLineEdit, QToolBar, QAction, QTabWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

try:
    from PyQt5 import QtGui
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt5', 'PyQtWebEngine'])
    from PyQt5 import QtGui

# Homepage HTML directly in code (dark theme)
HOMEPAGE_HTML = '''
<html>
<head>
<title>FireSeed2</title>
<style>
    body { background-color: #1e1e1e; color: #cfcfcf; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column; }
    h1 { color: #ff6f61; }
    p { color: #aaaaaa; }
</style>
</head>
<body>
<h1>Welcome to FireSeed2!</h1>
<p>This is the built-in dark homepage.</p>
</body>
</html>
'''

class BrowserTab(QWidget):
    def __init__(self, url=HOMEPAGE_HTML):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.web = QWebEngineView()
        self.web.page().profile().setHttpAcceptLanguage('en-US,en;q=0.9')  # Force English
        self.layout.addWidget(self.web)
        self.setLayout(self.layout)
        self.load_url(url)

    def load_url(self, url):
        if url == 'about:home':
            self.web.setHtml(HOMEPAGE_HTML)
        else:
            self.web.load(QUrl(url))

class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FireSeed2')
        self.resize(1200, 800)
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._add_tab('about:home')

        nav = QToolBar('Navigation')
        self.addToolBar(nav)
        self.back_act = QAction('◀', self)
        self.forward_act = QAction('▶', self)
        self.reload_act = QAction('⟳', self)
        self.home_act = QAction('🏠', self)
        self.newtab_act = QAction('🗂', self)
        self.addr = QLineEdit(self)
        nav.addAction(self.back_act)
        nav.addAction(self.forward_act)
        nav.addAction(self.reload_act)
        nav.addAction(self.home_act)
        nav.addAction(self.newtab_act)
        nav.addWidget(self.addr)

        self.back_act.triggered.connect(self.current_tab().web.back)
        self.forward_act.triggered.connect(self.current_tab().web.forward)
        self.reload_act.triggered.connect(self.current_tab().web.reload)
        self.home_act.triggered.connect(lambda: self.current_tab().load_url('about:home'))
        self.newtab_act.triggered.connect(lambda: self._add_tab('about:home'))
        self.addr.returnPressed.connect(self._on_enter_address)
        self.tabs.currentChanged.connect(self._on_tab_change)

    def _add_tab(self, url):
        tab = BrowserTab(url)
        index = self.tabs.addTab(tab, 'New Tab')
        self.tabs.setCurrentIndex(index)
        tab.web.urlChanged.connect(lambda qurl, t=tab: self._update_tab_title(t, qurl))

    def _update_tab_title(self, tab, qurl):
        index = self.tabs.indexOf(tab)
        if index >= 0:
            self.tabs.setTabText(index, qurl.toString())
            if self.tabs.currentWidget() == tab:
                self.addr.setText(qurl.toString())

    def _on_tab_change(self, index):
        tab = self.current_tab()
        if tab:
            url = tab.web.url().toString()
            self.addr.setText(url)
            self.back_act.triggered.disconnect()
            self.forward_act.triggered.disconnect()
            self.reload_act.triggered.disconnect()
            self.back_act.triggered.connect(tab.web.back)
            self.forward_act.triggered.connect(tab.web.forward)
            self.reload_act.triggered.connect(tab.web.reload)

    def current_tab(self):
        return self.tabs.currentWidget()

    def _on_enter_address(self):
        txt = self.addr.text().strip()
        if not txt:
            return
        if txt == 'about:home':
            self.current_tab().load_url('about:home')
        elif not txt.startswith(('http://', 'https://', 'file://')):
            txt = 'http://' + txt
        self.current_tab().load_url(txt)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BrowserApp()
    window.show()
    sys.exit(app.exec_())
