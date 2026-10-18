"""HX Studio - PyQt5 IDE"""
import sys, os, re, json, queue, threading, time

_HX = None
def hx():
    global _HX
    if _HX is None:
        import hx as m
        _HX = m
    return _HX

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QSplitter, QMenuBar, QMenu, QAction, QTabWidget, QPlainTextEdit,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QLineEdit, QPushButton, QLabel,
    QStatusBar, QMessageBox, QFileDialog, QCheckBox, QSizePolicy, QStackedWidget,
    QShortcut, QInputDialog, QScrollArea, QListWidget, QListWidgetItem, QToolButton
)
from PyQt5.QtCore import Qt, QTimer, QSize, QRect, QRegularExpression
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QKeySequence,
    QPainter, QTextFormat, QTextCursor, QPixmap
)

C_BG = "#1e1e1e"
C_SIDEBAR = "#252526"
C_ACTIVITY = "#333333"
C_TAB_BG = "#2d2d30"
C_FG = "#cccccc"
C_FG_DIM = "#858585"
C_BORDER = "#2d2d30"
C_ACCENT = "#0e639c"
C_STATUS = "#007acc"
C_GUTTER = "#1e1e1e"
C_GUTTER_FG = "#858585"
C_CURRENT_LINE = "#2a2d2e"

H_KEYWORD = "#569cd6"
H_BUILTIN = "#dcdcaa"
H_STRING = "#ce9178"
H_NUMBER = "#b5cea8"
H_COMMENT = "#6a9955"

KEYWORDS = ["let","if","else","while","for","break","continue","del",
            "return","true","false","null","and","or","not","try","catch"]
BUILTINS = [
    "print","input","scanf","help","len","push","keys","items","has","set",
    "type","str","num","upper","lower","trim","split","join","min","max","abs",
    "sqrt","sin","cos","tan","floor","ceil","round","random","range","PI",
    "gwin","gline","grect","gcircle","gtext","gclear","gsleep",
    "gwaitkey","gwaitclick","gkeydown","gclick",
    "readfile","writefile","appendfile","exists","files","openfile","openurl","runapp",
    "http_get","http_download","bg_run","md5","sha256","unzip","zipinfo",
    "uiwin","uibtn","uilabel","uiheading","uiinput","uitext","uicheck",
    "uiradio","uicombo","uilist","uirange","uiprogress","uiimage","uitable",
    "uipanel","uiseparator","uitabs","uion","uiget","uiset","uirun",
]

QSS = """
QMainWindow, QWidget { background: #1e1e1e; color: #cccccc; }
QMenuBar { background: #2d2d30; color: #cccccc; border: none; padding: 2px; }
QMenuBar::item { background: transparent; padding: 4px 10px; }
QMenuBar::item:selected { background: #0e639c; }
QMenu { background: #2d2d30; color: #cccccc; border: 1px solid #3e3e42; padding: 4px; }
QMenu::item { padding: 5px 24px 5px 20px; }
QMenu::item:selected { background: #0e639c; }
QMenu::separator { height: 1px; background: #3e3e42; margin: 4px 0; }
QSplitter::handle { background: #2d2d30; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QTabWidget::pane { border: none; background: #1e1e1e; }
QTabBar::tab {
    background: #2d2d30; color: #858585; border: none;
    padding: 6px 14px; margin-right: 1px;
}
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; }
QTabBar::tab:hover:!selected { background: #37373d; }
QPlainTextEdit, QTextEdit {
    background: #1e1e1e; color: #d4d4d4;
    border: none; selection-background-color: #264f78;
}
QTreeWidget {
    background: #252526; color: #cccccc; border: none;
    outline: none;
}
QTreeWidget::item { padding: 3px 6px; }
QTreeWidget::item:selected { background: #094771; }
QTreeWidget::item:hover { background: #2a2d2e; }
QLineEdit {
    background: #3c3c3c; color: #cccccc; border: 1px solid #3c3c3c;
    border-radius: 3px; padding: 4px 8px; selection-background-color: #264f78;
}
QLineEdit:focus { border: 1px solid #0e639c; }
QPushButton {
    background: #0e639c; color: #ffffff; border: none;
    border-radius: 3px; padding: 6px 14px;
}
QPushButton:hover { background: #1177bb; }
QPushButton:disabled { background: #3a3a3d; color: #858585; }
QCheckBox { color: #cccccc; }
QCheckBox::indicator { width: 14px; height: 14px; }
QStatusBar { background: #007acc; color: #ffffff; }
QScrollBar:vertical { background: #1e1e1e; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #424242; min-height: 20px; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #4f4f4f; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1e1e1e; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #424242; min-width: 20px; border-radius: 6px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QListWidget { background: #252526; color: #cccccc; border: none; outline: none; }
QListWidget::item { padding: 3px 6px; }
QListWidget::item:selected { background: #094771; }
"""


class HXHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(H_KEYWORD))
        fmt.setFontWeight(QFont.Bold)
        for kw in KEYWORDS:
            self.rules.append((QRegularExpression(r"\b" + kw + r"\b"), fmt))
        fmt2 = QTextCharFormat()
        fmt2.setForeground(QColor(H_BUILTIN))
        for fn in BUILTINS:
            self.rules.append((QRegularExpression(r"\b" + fn + r"\b"), fmt2))
        fmt3 = QTextCharFormat()
        fmt3.setForeground(QColor(H_NUMBER))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), fmt3))
        fmt4 = QTextCharFormat()
        fmt4.setForeground(QColor(H_STRING))
        self.rules.append((QRegularExpression(r'"[^"]*"'), fmt4))
        self.rules.append((QRegularExpression(r"'[^']*'"), fmt4))
        fmt5 = QTextCharFormat()
        fmt5.setForeground(QColor(H_COMMENT))
        fmt5.setFontItalic(True)
        self.rules.append((QRegularExpression(r"#[^\n]*"), fmt5))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor
    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)
    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self._err_line = 0
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        self.highlighter = HXHighlighter(self.document())
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setTabStopWidth(self.fontMetrics().width(' ') * 4)

    def lineNumberAreaWidth(self):
        digits = 1
        m = max(1, self.blockCount())
        while m >= 10:
            m //= 10
            digits += 1
        return 12 + self.fontMetrics().width('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(),
                                              self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(C_GUTTER))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                if blockNumber + 1 == self._err_line:
                    painter.setPen(QColor("#f14c4c"))
                else:
                    painter.setPen(QColor(C_GUTTER_FG))
                painter.drawText(0, int(top), self.lineNumberArea.width() - 6,
                                 self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        selections = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(C_CURRENT_LINE))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        if self._err_line > 0:
            sel2 = QTextEdit.ExtraSelection()
            sel2.format.setBackground(QColor("#5a1d1d"))
            sel2.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel2.cursor = QTextCursor(self.document().findBlockByNumber(self._err_line - 1))
            selections.append(sel2)
        self.setExtraSelections(selections)

    def set_error_line(self, line):
        self._err_line = line
        self.highlightCurrentLine()
        self.lineNumberArea.update()

    def goto_line(self, line, col=0):
        block = self.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, col)
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()


class HXIDE(QMainWindow):
    def __init__(self, initial_path=None):
        super().__init__()
        self.setWindowTitle("HX Studio")
        self.resize(1360, 880)
        self.setStyleSheet(QSS)
        self.setMinimumSize(900, 600)

        self.current_path = None
        self.current_editor = None
        self.interp = None
        self.input_queue = queue.Queue()
        self.input_waiting = False
        self.ai_q = queue.Queue()
        self.ai_busy = False

        self._build_ui()
        self._build_menu()
        self._build_status()
        self._refresh_explorer()
        self._ai_welcome()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(60)

        if initial_path and os.path.exists(initial_path):
            self.open_file(initial_path)
        else:
            self.load_text(self._sample(), None)

    def _sample(self):
        return '''# HX 语言示例
fib(n) {
    if (n < 2) { return n; }
    return fib(n - 1) + fib(n - 2);
}

print("fib(10) =", fib(10));

for (i = 0; i < 5; i += 1) {
    print("i =", i);
}
'''

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.setHandleWidth(1)

        self.activity = QFrame()
        self.activity.setFixedWidth(48)
        self.activity.setStyleSheet("QFrame{background:#333333;}")
        av = QVBoxLayout(self.activity)
        av.setContentsMargins(0, 8, 0, 8)
        av.setSpacing(4)
        self.act_btns = {}
        for key, icon, tip in [
            ("files", "F", "资源管理器"),
            ("search", "S", "搜索"),
            ("ai", "A", "小智 AI"),
            ("settings", "G", "设置"),
        ]:
            b = QToolButton()
            b.setText(icon)
            b.setToolTip(tip)
            b.setFixedSize(40, 40)
            b.clicked.connect(lambda _, k=key: self.set_activity(k))
            av.addWidget(b)
            self.act_btns[key] = b
        av.addStretch()
        self.main_split.addWidget(self.activity)

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("QFrame{background:#252526;}")
        sv = QVBoxLayout(self.sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        self.sidebar_title = QLabel("资源管理器")
        self.sidebar_title.setStyleSheet("QLabel{background:#252526;color:#bbbbbb;font-weight:bold;padding:10px 12px;}")
        sv.addWidget(self.sidebar_title)
        self.sidebar_stack = QStackedWidget()
        sv.addWidget(self.sidebar_stack, 1)

        self.explorer = QTreeWidget()
        self.explorer.setHeaderHidden(True)
        self.explorer.itemDoubleClicked.connect(self._explorer_open)
        self.sidebar_stack.addWidget(self.explorer)

        self.search_page = QWidget()
        sp = QVBoxLayout(self.search_page)
        sp.setContentsMargins(8, 8, 8, 8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索所有 .hxg 文件")
        self.search_input.returnPressed.connect(self._do_search)
        self.search_input.textChanged.connect(self._do_search_auto)
        sp.addWidget(self.search_input)
        self.search_result = QListWidget()
        self.search_result.itemDoubleClicked.connect(self._search_goto)
        sp.addWidget(self.search_result, 1)
        self.sidebar_stack.addWidget(self.search_page)

        ph1 = QLabel("小智在右侧面板")
        ph1.setStyleSheet("QLabel{color:#858585;padding:20px;}")
        self.sidebar_stack.addWidget(ph1)
        ph2 = QLabel("设置")
        ph2.setStyleSheet("QLabel{color:#858585;padding:20px;}")
        self.sidebar_stack.addWidget(ph2)

        self.main_split.addWidget(self.sidebar)

        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        self.crumb = QLabel("")
        self.crumb.setStyleSheet("QLabel{background:#1e1e1e;color:#858585;padding:4px 14px;font-size:9pt;}")
        cv.addWidget(self.crumb)

        vsplit = QSplitter(Qt.Vertical)
        vsplit.setHandleWidth(1)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)
        vsplit.addWidget(self.tabs)

        self.panel = QTabWidget()
        self.out_view = QTextEdit()
        self.out_view.setReadOnly(True)
        self.out_view.setFont(QFont("Consolas", 10))
        self.var_view = QTextEdit()
        self.var_view.setReadOnly(True)
        self.var_view.setFont(QFont("Consolas", 10))
        self.prob_view = QTextEdit()
        self.prob_view.setReadOnly(True)
        self.prob_view.setFont(QFont("Consolas", 10))
        self.inp_page = QWidget()
        ip = QHBoxLayout(self.inp_page)
        ip.setContentsMargins(8, 6, 8, 6)
        self.inp_entry = QLineEdit()
        self.inp_entry.setFont(QFont("Consolas", 11))
        self.inp_entry.returnPressed.connect(self._submit_input)
        self.inp_btn = QPushButton("发送")
        self.inp_btn.clicked.connect(self._submit_input)
        ip.addWidget(self.inp_entry, 1)
        ip.addWidget(self.inp_btn)
        self.panel.addTab(self.out_view, "输出")
        self.panel.addTab(self.var_view, "变量")
        self.panel.addTab(self.prob_view, "问题")
        self.panel.addTab(self.inp_page, "输入")
        vsplit.addWidget(self.panel)
        vsplit.setSizes([600, 160])
        cv.addWidget(vsplit, 1)
        self.main_split.addWidget(center)

        self.ai_panel = QFrame()
        self.ai_panel.setFixedWidth(380)
        self.ai_panel.setStyleSheet("QFrame{background:#252526;}")
        ap = QVBoxLayout(self.ai_panel)
        ap.setContentsMargins(0, 0, 0, 0)
        ap.setSpacing(0)
        ai_head = QFrame()
        ai_head.setStyleSheet("QFrame{background:#2d2d30;}")
        ah = QHBoxLayout(ai_head)
        ah.setContentsMargins(12, 6, 8, 6)
        t1 = QLabel("小智")
        t1.setStyleSheet("QLabel{color:#9cdcfe;font-weight:bold;font-size:10pt;}")
        ah.addWidget(t1)
        t2 = QLabel("HX 向导")
        t2.setStyleSheet("QLabel{color:#858585;font-size:9pt;}")
        ah.addWidget(t2)
        ah.addStretch()
        cfg_btn = QToolButton()
        cfg_btn.setText("设置")
        cfg_btn.setStyleSheet("QToolButton{color:#858585;background:transparent;border:none;padding:4px 8px;}")
        cfg_btn.clicked.connect(self._ai_config)
        ah.addWidget(cfg_btn)
        ap.addWidget(ai_head)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("QTextEdit{background:#252526;color:#d4d4d4;border:none;padding:8px;}")
        ap.addWidget(self.chat, 1)

        ai_bottom = QFrame()
        ai_bottom.setStyleSheet("QFrame{background:#2d2d30;}")
        ab = QVBoxLayout(ai_bottom)
        ab.setContentsMargins(10, 6, 10, 10)
        ab.setSpacing(4)
        self.ai_attach = QCheckBox("附带当前代码")
        self.ai_attach.setChecked(True)
        self.ai_attach.setStyleSheet("QCheckBox{color:#858585;}")
        ab.addWidget(self.ai_attach)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.ai_input = QTextEdit()
        self.ai_input.setFixedHeight(70)
        self.ai_input.setStyleSheet("QTextEdit{background:#3c3c3c;color:#cccccc;border:none;border-radius:3px;padding:6px;}")
        row.addWidget(self.ai_input, 1)
        self.ai_send = QPushButton("发送")
        self.ai_send.setFixedSize(60, 70)
        self.ai_send.clicked.connect(self._ai_send)
        row.addWidget(self.ai_send)
        ab.addLayout(row)
        ap.addWidget(ai_bottom)
        self.main_split.addWidget(self.ai_panel)

        self.main_split.setSizes([48, 240, 700, 380])
        self.main_split.setStretchFactor(0, 0)
        self.main_split.setStretchFactor(1, 0)
        self.main_split.setStretchFactor(2, 1)
        self.main_split.setStretchFactor(3, 0)
        outer.addWidget(self.main_split, 1)
        self.set_activity("files")

    def _build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu("文件")
        self._action(m, "新建            Ctrl+N", self.do_new, "Ctrl+N")
        self._action(m, "打开…           Ctrl+O", self.do_open, "Ctrl+O")
        self._action(m, "保存            Ctrl+S", self.do_save, "Ctrl+S")
        self._action(m, "另存为…", self.do_save_as)
        m.addSeparator()
        self._action(m, "退出", self.close)
        m = mb.addMenu("编辑")
        self._action(m, "撤销", lambda: self._editor_cmd("undo"), "Ctrl+Z")
        self._action(m, "重做", lambda: self._editor_cmd("redo"), "Ctrl+Y")
        m.addSeparator()
        self._action(m, "清空编辑器", self.do_clear)
        m = mb.addMenu("运行")
        self._action(m, "运行            F5", self.do_run, "F5")
        self._action(m, "单步            F10", self.do_step, "F10")
        m.addSeparator()
        self._action(m, "载入示例", self.do_sample)
        m = mb.addMenu("视图")
        self._action(m, "切换侧边栏      Ctrl+B", self.toggle_sidebar, "Ctrl+B")
        self._action(m, "显示/隐藏 小智", self.toggle_ai)
        m.addSeparator()
        self._action(m, "UI 设计器        Ctrl+U", self.open_designer, "Ctrl+U")
        m = mb.addMenu("帮助")
        self._action(m, "语法速查", self.do_cheat)
        self._action(m, "关于 HX Studio", self.do_about)

    def _action(self, menu, text, fn, shortcut=None):
        act = QAction(text, self)
        act.triggered.connect(fn)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        menu.addAction(act)
        return act

    def _build_status(self):
        sb = self.statusBar()
        sb.setStyleSheet("QStatusBar{background:#007acc;color:#ffffff;} QStatusBar::item{border:none;}")
        self.st_branch = QLabel("main")
        self.st_err = QLabel("x 0  ! 0")
        self.st_msg = QLabel("")
        self.st_run = QLabel("")
        self.st_pos = QLabel("行 1, 列 1")
        self.st_enc = QLabel("UTF-8")
        self.st_lang = QLabel("HX")
        for w in (self.st_branch, self.st_err, self.st_msg, self.st_run, self.st_pos, self.st_enc, self.st_lang):
            w.setStyleSheet("QLabel{color:#ffffff;padding:0 10px;}")
        sb.addWidget(self.st_branch)
        sb.addWidget(self.st_err)
        sb.addWidget(self.st_msg, 1)
        sb.addPermanentWidget(self.st_run)
        sb.addPermanentWidget(self.st_pos)
        sb.addPermanentWidget(self.st_enc)
        sb.addPermanentWidget(self.st_lang)

    def set_activity(self, key):
        for k, b in self.act_btns.items():
            if k == key:
                b.setStyleSheet("QToolButton{color:#ffffff;background:transparent;border-left:2px solid #ffffff;font-size:15px;font-weight:bold;}")
            else:
                b.setStyleSheet("QToolButton{color:#858585;background:transparent;border:none;font-size:15px;font-weight:bold;} QToolButton:hover{background:#2a2d2e;color:#ffffff;}")
        titles = {"files": "资源管理器", "search": "搜索", "ai": "小智", "settings": "设置"}
        self.sidebar_title.setText(titles.get(key, ""))
        idx = {"files": 0, "search": 1, "ai": 2, "settings": 3}.get(key, 0)
        self.sidebar_stack.setCurrentIndex(idx)
        if key == "files":
            self._refresh_explorer()
        if not self.sidebar.isVisible():
            self.sidebar.setVisible(True)

    def toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def toggle_ai(self):
        self.ai_panel.setVisible(not self.ai_panel.isVisible())

    def _refresh_explorer(self):
        self.explorer.clear()
        project_dir = os.getcwd()
        if not os.path.isdir(project_dir):
            return
        root = QTreeWidgetItem([os.path.basename(project_dir) or project_dir])
        root.setExpanded(True)
        self.explorer.addTopLevelItem(root)
        try:
            files = sorted(f for f in os.listdir(project_dir) if f.endswith(".hxg"))
        except Exception:
            files = []
        for f in files:
            it = QTreeWidgetItem([f])
            it.setData(0, Qt.UserRole, os.path.join(project_dir, f))
            root.addChild(it)

    def _explorer_open(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path and os.path.isfile(path):
            self.open_file(path)

    def _do_search_auto(self, text):
        if len(text) >= 2:
            self._do_search()

    def _do_search(self):
        kw = self.search_input.text().strip()
        self.search_result.clear()
        if not kw:
            return
        project_dir = os.getcwd()
        try:
            files = sorted(f for f in os.listdir(project_dir) if f.endswith(".hxg"))
        except Exception:
            files = []
        total = 0
        for fname in files:
            full = os.path.join(project_dir, fname)
            try:
                with open(full, encoding="utf-8") as fp:
                    for lineno, line in enumerate(fp, 1):
                        if kw.lower() in line.lower():
                            item = QListWidgetItem("%s:%d  %s" % (fname, lineno, line.strip()[:80]))
                            item.setData(Qt.UserRole, (full, lineno))
                            self.search_result.addItem(item)
                            total += 1
                            if total >= 500:
                                break
            except Exception:
                continue
            if total >= 500:
                break
        self.sidebar_title.setText("搜索（%d 个结果）" % total)

    def _search_goto(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        path, lineno = data
        self.open_file(path)
        if self.current_editor:
            self.current_editor.goto_line(lineno)

    def _current_editor(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _new_tab(self, title="未命名.hxg"):
        ed = CodeEditor()
        ed.cursorPositionChanged.connect(self._update_pos)
        self.tabs.addTab(ed, title)
        self.tabs.setCurrentWidget(ed)
        self.current_editor = ed
        return ed

    def _tab_changed(self, idx):
        self.current_editor = self._current_editor()
        self._update_pos()
        self._update_crumb()

    def _close_tab(self, idx):
        w = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        if w:
            w.deleteLater()

    def _update_crumb(self):
        if self.current_path:
            self.crumb.setText(os.path.dirname(self.current_path) + "  >  " + os.path.basename(self.current_path))
        else:
            self.crumb.setText("")

    def _update_pos(self):
        ed = self._current_editor()
        if ed is None:
            return
        c = ed.textCursor()
        self.st_pos.setText("行 %d, 列 %d" % (c.blockNumber() + 1, c.columnNumber() + 1))

    def _editor_cmd(self, cmd):
        ed = self._current_editor()
        if ed:
            getattr(ed, cmd)()

    def load_text(self, text, path=None):
        ed = self._current_editor()
        if ed is None or (path is None and ed.toPlainText()):
            ed = self._new_tab(os.path.basename(path) if path else "未命名.hxg")
        ed.setPlainText(text)
        self.current_path = path
        if path:
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path))
            ed._path = path
        self._update_crumb()
        self._clear_error()

    def open_file(self, path):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if getattr(w, "_path", None) == path:
                self.tabs.setCurrentIndex(i)
                self.current_path = path
                self._update_crumb()
                return
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))
            return
        ed = self._new_tab(os.path.basename(path))
        ed.setPlainText(text)
        ed._path = path
        self.current_path = path
        self._update_crumb()

    def do_new(self):
        self._new_tab("未命名.hxg")
        self.current_path = None
        self._update_crumb()

    def do_open(self):
        p, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "HX 源码 (*.hxg);;所有文件 (*.*)")
        if p:
            self.open_file(p)

    def do_save(self):
        p = self.current_path
        if not p:
            p, _ = QFileDialog.getSaveFileName(self, "保存", "", "HX 源码 (*.hxg)")
            if not p:
                return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self._current_editor().toPlainText())
            self.current_path = p
            if self.current_editor:
                self.current_editor._path = p
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(p))
            self._update_crumb()
            self.st_msg.setText("已保存 " + os.path.basename(p))
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def do_save_as(self):
        p, _ = QFileDialog.getSaveFileName(self, "另存为", "", "HX 源码 (*.hxg)")
        if p:
            self.current_path = None
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(self._current_editor().toPlainText())
                self.current_path = p
                if self.current_editor:
                    self.current_editor._path = p
                self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(p))
                self._update_crumb()
                self.st_msg.setText("已保存 " + os.path.basename(p))
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def do_clear(self):
        ed = self._current_editor()
        if ed:
            ed.clear()
            self._clear_error()

    def do_sample(self):
        self.load_text(self._sample(), None)

    def do_run(self):
        ed = self._current_editor()
        if ed is None:
            return
        src = ed.toPlainText()
        self._clear_error()
        try:
            m = hx()
            self.interp = m.Interp()
            self._bind_input()
            self.interp.run(m.Parser(m.tokenize(src)).program())
            self.out_view.setPlainText(self.interp.text())
            self._show_vars(self.interp)
            self.st_run.setText("运行完成")
            self.panel.setCurrentIndex(0)
        except Exception as e:
            self._show_error(str(e))
            self.st_run.setText("运行失败")

    def do_step(self):
        QMessageBox.information(self, "提示", "PyQt5 版 IDE 的单步调试仍在完善，先用 F5 运行。")

    def _show_error(self, msg):
        self.prob_view.setPlainText(msg)
        self.panel.setCurrentIndex(2)
        self.st_err.setText("x 1  ! 0")
        self.st_msg.setText(msg)
        ed = self._current_editor()
        if ed:
            mm = re.search(r"第 (\d+) 行", msg)
            if mm:
                ln = int(mm.group(1))
                ed.set_error_line(ln)
                ed.goto_line(ln)

    def _clear_error(self):
        self.prob_view.clear()
        self.st_err.setText("x 0  ! 0")
        self.st_msg.setText("")
        ed = self._current_editor()
        if ed:
            ed.set_error_line(0)

    def _show_vars(self, interp):
        try:
            d = interp.globals.vars
            lines = []
            for k, v in d.items():
                if isinstance(v, (int, float, str, list, dict, bool)) or v is None:
                    lines.append("%s = %r" % (k, v))
            self.var_view.setPlainText("\n".join(lines))
        except Exception:
            pass

    def _bind_input(self):
        self.input_waiting = False
        def ask():
            self.panel.setCurrentIndex(3)
            self.input_waiting = True
            self.inp_entry.clear()
            self.inp_entry.setFocus()
            while True:
                try:
                    v = self.input_queue.get_nowait()
                    self.input_waiting = False
                    return v
                except queue.Empty:
                    QApplication.processEvents()
                    time.sleep(0.02)
        self.interp.ask_fn = ask

    def _submit_input(self):
        if self.input_waiting:
            self.input_queue.put(self.inp_entry.text())
            self.inp_entry.clear()

    def _ai_config(self):
        m = hx()
        cfg = m.ai_load_config()
        base, ok = QInputDialog.getText(self, "AI 配置", "Base URL", text=cfg.get("base_url", ""))
        if not ok:
            return
        key, ok = QInputDialog.getText(self, "AI 配置", "API Key", text=cfg.get("api_key", ""))
        if not ok:
            return
        model, ok = QInputDialog.getText(self, "AI 配置", "Model", text=cfg.get("model", ""))
        if not ok:
            return
        cfg["base_url"] = base.strip()
        cfg["api_key"] = key.strip()
        cfg["model"] = model.strip()
        m.ai_save_config(cfg)
        self.chat.append("配置已保存。\n")

    def _ai_welcome(self):
        self.chat.clear()
        self.chat.append("你好，我是小智。\n\n有 HX 语言的问题直接问，也可以让我帮你写代码。\n")

    def _ai_send(self):
        m = hx()
        text = self.ai_input.toPlainText().strip()
        if not text or self.ai_busy:
            return
        cfg = m.ai_load_config()
        if not cfg.get("base_url") or not cfg.get("api_key"):
            QMessageBox.information(self, "提示", "请先点击右上角「设置」配置 AI 接口")
            return
        self.chat.append("\n你：" + text + "\n")
        self.ai_input.clear()
        self.ai_busy = True
        self.ai_send.setEnabled(False)
        self.ai_send.setText("...")
        self.chat.append("小智：")

        sys_prompt = getattr(m, "HX_SYSTEM_PROMPT", None)
        if not sys_prompt:
            sys_prompt = "你是 HX 语言编程助手，回答简洁，代码用 HX 语法。"
        messages = [{"role": "system", "content": sys_prompt}]
        if self.ai_attach.isChecked():
            ed = self._current_editor()
            if ed:
                fence = chr(96) * 3
                messages.append({"role": "user", "content": "当前代码：\n" + fence + "\n" + ed.toPlainText()[:4000] + "\n" + fence})
        messages.append({"role": "user", "content": text})

        def worker():
            try:
                for chunk in m.ai_chat_stream(cfg, messages, lambda c: None):
                    self.ai_q.put(("chunk", chunk))
                self.ai_q.put(("done", None))
            except Exception as e:
                self.ai_q.put(("err", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        while True:
            try:
                kind, payload = self.ai_q.get_nowait()
            except queue.Empty:
                break
            if kind == "chunk":
                self.chat.moveCursor(QTextCursor.End)
                self.chat.insertPlainText(payload)
                self.chat.moveCursor(QTextCursor.End)
            elif kind == "done":
                self.ai_busy = False
                self.ai_send.setEnabled(True)
                self.ai_send.setText("发送")
                self.chat.append("\n")
            elif kind == "err":
                self.ai_busy = False
                self.ai_send.setEnabled(True)
                self.ai_send.setText("发送")
                self.chat.append("\n[错误] " + payload + "\n")

    def do_cheat(self):
        m = hx()
        text = m.cheatsheet_text()
        dlg = QMessageBox(self)
        dlg.setWindowTitle("HX 语法速查")
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.exec_()

    def do_about(self):
        QMessageBox.about(self, "关于 HX Studio",
                          "HX Studio\nHX 语言集成开发环境\n\nPyQt5 版\n内置小智 AI 助手")

    def open_designer(self):
        try:
            import hx_designer_qt
        except ImportError as e:
            QMessageBox.warning(self, "提示", "找不到 hx_designer_qt.py：" + str(e))
            return
        ed = self._current_editor()
        items = []
        if ed:
            m = hx()
            items = m.ui_parse_code(ed.toPlainText())
        dlg = hx_designer_qt.DesignerDialog(self, initial_items=items)
        dlg.exec_()
        if dlg.result_code and ed:
            cursor = ed.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText("\n" + dlg.result_code + "\n")
            self.st_msg.setText("已插入 %d 个组件的代码" % len(dlg.items))


def build_gui_qt(initial_path=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv if sys.argv else [""])
        app.setStyle("Fusion")
    win = HXIDE(initial_path)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    build_gui_qt(sys.argv[1] if len(sys.argv) > 1 else None)
