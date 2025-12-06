from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt, QUrl

def set_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

START_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>FireSeed Start</title>
    <style>
        body {
            background: #23272e;
            color: #fff;
            font-family: Arial, sans-serif;
            text-align: center;
            margin-top: 120px;
        }
        h1 { font-size: 3em; margin-bottom: 0.2em; }
        p { color: #aaa; }
        .logo {
            font-size: 5em;
            margin-bottom: 0.5em;
        }
        a {
            color: #42aaff;
            text-decoration: none;
            margin: 0 10px;
        }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="logo">🔥</div>
    <h1>FireSeed Browser</h1>
    <p>Добро пожаловать! Введите адрес сайта в строке выше.</p>
    <p>
        <a href="https://www.google.com">Google</a>
        <a href="https://www.youtube.com">YouTube</a>
        <a href="https://github.com">GitHub</a>
        <a href="https://www.appleworm.io">AppleWorm</a>
        <a href="https://play.google.com">GooglePlay</a>
        <a href="https://www.microsoft.com">Microsoft</a>
        <a href="https://www.apple.com">Apple</a>
        <a href="https://www.amazon.com">Amazon</a>
        <a href="https://www.facebook.com">Facebook</a>
        <a href="https://www.twitter.com">Twitter</a>
        <a href="https://www.instagram.com">Instagram</a>
        <a href="https://www.reddit.com">Reddit</a>
        <a href="https://www.wikipedia.org">Wikipedia</a>
        <a href="https://www.firefox.com">FireFox</a>
        <a href="https://www.opera.com">Opera</a>
        <a href="https://www.microsoft.com/edge">Edge</a>
        <a href="https://www.brave.com">Brave</a>
        <a href="https://github.com/Scripter456/FireSeed">FireSeedOfficial</a>
        <a href="https://youareanidiot.wzq02.top">click on me</a>

    </p>
</body>
</html>
"""

class ConsoleTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.layout.addWidget(self.console)
        self.setLayout(self.layout)

    def write(self, text):
        self.console.append(text)

class BrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # Панель навигации
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.forward_btn = QPushButton("→")
        self.reload_btn = QPushButton("⟳")
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите адрес сайта и нажмите Enter")

        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.reload_btn)
        nav_layout.addWidget(self.url_bar)

        self.webview = QWebEngineView()

        self.layout.addLayout(nav_layout)
        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)

        self.url_bar.returnPressed.connect(self.load_url)
        self.webview.urlChanged.connect(self.update_url_bar)
        self.webview.setHtml(START_PAGE)

        self.back_btn.clicked.connect(self.webview.back)
        self.forward_btn.clicked.connect(self.webview.forward)
        self.reload_btn.clicked.connect(self.webview.reload)

    def load_url(self):
        url = self.url_bar.text()
        if not url.startswith("http"):
            url = "http://" + url
        self.webview.setUrl(QUrl(url))

    def update_url_bar(self, qurl):
        self.url_bar.setText(qurl.toString())
        # Логируем переход в консоль, если возможно
        main = self.parent()
        while main and not isinstance(main, Browser):
            main = main.parent()
        if main and hasattr(main, "log_to_console"):
            main.log_to_console(f"Переход: {qurl.toString()}")

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FireSeed Browser")
        self.setGeometry(200, 200, 1100, 750)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.check_plus_tab)

        # Добавляем вкладку консоли
        self.console_tab = ConsoleTab(self)
        self.console_tab_idx = self.tabs.addTab(self.console_tab, "Консоль")

        self.setCentralWidget(self.tabs)
        self.add_new_tab()  # Открыть первую вкладку
        self.add_plus_tab() # Добавить вкладку "+"

    def log_to_console(self, text):
        self.console_tab.write(text)

    def add_new_tab(self, url=None):
        tab = BrowserTab(self)
        idx = self.tabs.count() - 1 if self.has_plus_tab() else self.tabs.count()
        self.tabs.insertTab(idx, tab, "Новая вкладка")
        self.tabs.setCurrentIndex(idx)
        tab.webview.titleChanged.connect(lambda title, t=tab: self.update_tab_title(t, title))
        if url:
            tab.url_bar.setText(url)
            tab.load_url()

    def add_plus_tab(self):
        plus_tab = QWidget()
        idx = self.tabs.addTab(plus_tab, "+")
        self.tabs.setTabEnabled(idx, True)

    def has_plus_tab(self):
        return self.tabs.tabText(self.tabs.count() - 1) == "+"

    def check_plus_tab(self, index):
        if self.has_plus_tab() and index == self.tabs.count() - 1:
            self.add_new_tab()
            self.tabs.setCurrentIndex(self.tabs.count() - 2)

    def update_tab_title(self, tab, title):
        idx = self.tabs.indexOf(tab)
        if idx != -1:
            self.tabs.setTabText(idx, title if title else "Вкладка")

    def close_tab(self, index):
        if self.has_plus_tab() and index == self.tabs.count() - 1:
            return
        # Считаем количество обычных вкладок (без "+")
        normal_tabs = self.tabs.count() - 1 if self.has_plus_tab() else self.tabs.count()
        if normal_tabs > 1:
            self.tabs.removeTab(index)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    set_dark_theme(app)
    window = Browser()
    window.show()
    sys.exit(app.exec_())
