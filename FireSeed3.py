import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QAction,
    QTabWidget, QWidget, QVBoxLayout, QTextEdit, QDockWidget, QPushButton
)
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

try:
    from PyQt5 import QtGui
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt5', 'PyQtWebEngine'])
    from PyQt5 import QtGui

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
    def __init__(self, url):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.web = QWebEngineView()
        self.layout.addWidget(self.web)
        self.setLayout(self.layout)

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
        self._build_console()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # первая вкладка
        self.new_tab('about:home')

        nav = QToolBar("Navigation")
        self.addToolBar(nav)

        self.back_btn = QAction("◀", self)
        self.forward_btn = QAction("▶", self)
        self.reload_btn = QAction("⟳", self)
        self.home_btn = QAction("🏠", self)
        self.newtab_btn = QAction("🗂", self)
        self.console_btn = QAction("<>", self)

        self.addr = QLineEdit(self)

        nav.addAction(self.back_btn)
        nav.addAction(self.forward_btn)
        nav.addAction(self.reload_btn)
        nav.addAction(self.home_btn)
        nav.addAction(self.newtab_btn)
        nav.addAction(self.console_btn)
        nav.addWidget(self.addr)

        self.back_btn.triggered.connect(lambda: self.current().web.back())
        self.forward_btn.triggered.connect(lambda: self.current().web.forward())
        self.reload_btn.triggered.connect(lambda: self.current().web.reload())
        self.home_btn.triggered.connect(lambda: self.current().web.setHtml(HOMEPAGE_HTML))
        self.newtab_btn.triggered.connect(lambda: self.new_tab("about:home"))
        self.console_btn.triggered.connect(self.toggle_console)
        self.addr.returnPressed.connect(self.load_url)

        self.tabs.currentChanged.connect(self.sync_toolbar)

    def _build_console(self):
        self.console = QDockWidget("Developer Console", self)
        self.console.setVisible(False)

        self.console_area = QWidget()
        box = QVBoxLayout(self.console_area)

        self.code = QTextEdit()
        run = QPushButton("Run JS")

        run.clicked.connect(self.exec_js)

        box.addWidget(self.code)
        box.addWidget(run)
        self.console.setWidget(self.console_area)

        self.addDockWidget(2, self.console)

    def toggle_console(self):
        self.console.setVisible(not self.console.isVisible())

    def exec_js(self):
        js_code = self.code.toPlainText()
        tab = self.current()
        if tab:
            tab.web.page().runJavaScript(js_code)

    def new_tab(self, url):
        tab = BrowserTab(url)
        index = self.tabs.addTab(tab, "Tab")
        self.tabs.setCurrentIndex(index)
        tab.web.urlChanged.connect(lambda u, t=tab: self.update_title(t, u))

    def update_title(self, tab, qurl):
        ix = self.tabs.indexOf(tab)
        if ix >= 0:
            self.tabs.setTabText(ix, qurl.toString())

    def current(self):
        return self.tabs.currentWidget()

    def load_url(self):
        txt = self.addr.text().strip()
        if not txt:
            return
        if txt == "about:home":
            self.current().web.setHtml(HOMEPAGE_HTML)
        elif not txt.startswith("http"):
            txt = "http://" + txt
        self.current().web.load(QUrl(txt))

    def sync_toolbar(self):
        tab = self.current()
        if not tab:
            return
        try:
            self.addr.setText(tab.web.url().toString())
        except:
            self.addr.setText("")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = BrowserApp()
    w.show()
    sys.exit(app.exec_())
