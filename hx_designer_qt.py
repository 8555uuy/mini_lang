"""HX UI 设计器 - PyQt5 版"""
import sys, os, re, subprocess, tempfile

from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QSplitter, QPushButton, QLabel, QLineEdit, QScrollArea, QToolButton,
    QMessageBox, QGridLayout, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics

_HX = None
def hx():
    global _HX
    if _HX is None:
        import hx as m
        _HX = m
    return _HX

# 配色（与 IDE 一致）
C_BG = "#16181c"
C_PANEL = "#1c1f24"
C_HEAD = "#22262c"
C_BORDER = "#2c3138"
C_TEXT = "#d8dade"
C_MUTED = "#8b9199"
C_ACCENT = "#2f7fd8"
C_SEL = "#c2410c"
C_CANVAS = "#fafaf9"
C_GRID = "#eeedeb"
C_GRID2 = "#e4e2de"

QSS = """
QDialog { background: #16181c; }
QLabel { color: #d8dade; }
QPushButton {
    background: #1c1f24; color: #d8dade; border: 1px solid #2c3138;
    border-radius: 4px; padding: 5px 14px;
}
QPushButton:hover { background: #2a2f36; }
QPushButton#primary { background: #2f7fd8; border: none; color: #ffffff; }
QPushButton#primary:hover { background: #3d8fe6; }
QLineEdit {
    background: #16181c; color: #d8dade; border: 1px solid #2c3138;
    border-radius: 3px; padding: 4px 6px;
}
QLineEdit:focus { border: 1px solid #2f7fd8; }
QScrollArea { border: none; background: #1c1f24; }
QScrollArea > QWidget > QWidget { background: #1c1f24; }
QScrollBar:vertical { background: #16181c; width: 10px; }
QScrollBar::handle:vertical { background: #3a4048; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

FIELD_LABELS = {
    "id": "标识 (id)",
    "x": "横坐标 X",
    "y": "纵坐标 Y",
    "w": "宽度",
    "h": "高度",
    "text": "文字内容",
    "items": "选项（逗号分隔）",
    "max": "最大值",
}

NUM_FIELDS = ("x", "y", "w", "h", "max")


def comp_bbox(it):
    p = it["props"]
    w = p.get("w", 100)
    h = p.get("h", 30)
    k = it["kind"]
    if k == "check":
        w = max(60, 30 + len(str(p.get("text", ""))) * 14)
        h = 20
    elif k == "range":
        h = 30
    elif k == "separator":
        h = 1
    return p["x"], p["y"], w, h


class CanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.sel = None
        self.grid = True
        self.drag_item = None
        self.drag_ox = 0
        self.drag_oy = 0
        self.ghost = None
        self.setMouseTracking(True)
        self.setStyleSheet("background:%s;" % C_CANVAS)
        self.setMinimumSize(600, 500)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(C_CANVAS))
        w = self.width(); h = self.height()
        if self.grid:
            p.setPen(QPen(QColor(C_GRID), 1))
            for x in range(0, w, 10):
                p.drawLine(x, 0, x, h)
            for y in range(0, h, 10):
                p.drawLine(0, y, w, y)
            p.setPen(QPen(QColor(C_GRID2), 1))
            for x in range(0, w, 50):
                p.drawLine(x, 0, x, h)
            for y in range(0, h, 50):
                p.drawLine(0, y, w, y)
        for it in self.items:
            self._draw_item(p, it)
        # 选中控制点
        if self.sel is not None:
            x, y, cw, ch = comp_bbox(self.sel)
            p.setPen(QPen(QColor(C_SEL), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(x, y, cw, ch)
            p.setBrush(QBrush(QColor("#ffffff")))
            for (hx_, hy_) in [(x, y), (x + cw, y), (x, y + ch), (x + cw, y + ch)]:
                p.drawRect(hx_ - 4, hy_ - 4, 8, 8)
        # 拖放预览
        if self.ghost is not None:
            gx, gy, gw, gh = self.ghost
            pen = QPen(QColor(C_ACCENT), 2, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(gx, gy, gw, gh)

    def _draw_item(self, p, it):
        x, y, w, h = comp_bbox(it)
        props = it["props"]
        kind = it["kind"]
        is_sel = it is self.sel
        oc = QColor(C_SEL) if is_sel else QColor("#b8b6b1")
        p.setPen(QPen(oc, 2 if is_sel else 1))
        txt = str(props.get("text", ""))
        if kind == "title":
            p.setBrush(QBrush(QColor(C_CANVAS)))
            p.drawRect(x, y, w, h)
            f = QFont("Microsoft YaHei UI", 15); f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#1c1917"))
            p.drawText(QRect(x + 4, y, w - 8, h), Qt.AlignVCenter | Qt.AlignLeft, txt or "标题")
        elif kind == "label":
            p.setBrush(QBrush(QColor(C_CANVAS)))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 10))
            p.setPen(QColor("#1c1917"))
            p.drawText(QRect(x + 4, y, w - 8, h), Qt.AlignVCenter | Qt.AlignLeft, txt or "标签")
        elif kind == "button":
            p.setBrush(QBrush(QColor("#e8e6e2")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 10))
            p.setPen(QColor("#1c1917"))
            p.drawText(QRect(x, y, w, h), Qt.AlignCenter, txt or "按钮")
        elif kind == "input":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#b0aea9"))
            p.drawText(QRect(x + 6, y, w - 12, h), Qt.AlignVCenter | Qt.AlignLeft, "输入")
        elif kind == "text":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#b0aea9"))
            p.drawText(QRect(x + 6, y + 4, w - 12, 20), Qt.AlignLeft, "多行文本")
        elif kind == "check":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y + 3, 14, 14)
            p.setFont(QFont("Microsoft YaHei UI", 10))
            p.setPen(QColor("#1c1917"))
            p.drawText(QRect(x + 20, y, w, 20), Qt.AlignVCenter | Qt.AlignLeft, txt or "选项")
        elif kind == "radio":
            p.setBrush(QBrush(QColor(C_CANVAS)))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#1c1917"))
            its = props.get("items", [])
            for i, s in enumerate(its[:5]):
                yy = y + 10 + i * 22
                p.setBrush(QBrush(QColor("#ffffff")))
                p.setPen(QPen(oc, 1))
                p.drawEllipse(x + 6, yy - 5, 10, 10)
                p.setPen(QColor("#1c1917"))
                p.drawText(QRect(x + 22, yy - 9, w - 26, 18), Qt.AlignVCenter | Qt.AlignLeft, str(s))
        elif kind == "combo":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#1c1917"))
            p.drawText(QRect(x + 6, y, w - 24, h), Qt.AlignVCenter | Qt.AlignLeft, "下拉")
            p.setPen(QColor(C_MUTED))
            p.drawText(QRect(x + w - 18, y, 16, h), Qt.AlignCenter, "v")
        elif kind == "list":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#1c1917"))
            its = props.get("items", [])
            for i, s in enumerate(its[:8]):
                p.drawText(QRect(x + 8, y + 4 + i * 18, w - 12, 16), Qt.AlignVCenter | Qt.AlignLeft, str(s))
        elif kind == "range":
            p.setBrush(QBrush(QColor(C_CANVAS)))
            p.drawRect(x, y, w, 30)
            p.setPen(QPen(QColor("#c8c6c1"), 3))
            p.drawLine(x + 8, y + 15, x + w - 8, y + 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(C_ACCENT)))
            p.drawEllipse(x + 4, y + 9, 12, 12)
            p.setFont(QFont("Microsoft YaHei UI", 8))
            p.setPen(QColor(C_MUTED))
            p.drawText(QRect(x, y - 4, w, 14), Qt.AlignCenter, "0 - " + str(props.get("max", 100)))
        elif kind == "progress":
            p.setBrush(QBrush(QColor("#e8e6e2")))
            p.drawRect(x, y, w, h)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(C_ACCENT)))
            p.drawRect(x, y, int(w * 0.6), h)
        elif kind == "image":
            p.setBrush(QBrush(QColor("#f0eeea")))
            p.drawRect(x, y, w, h)
            p.setPen(QPen(QColor("#d8d6d1"), 1))
            p.drawLine(x, y, x + w, y + h)
            p.drawLine(x + w, y, x, y + h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor(C_MUTED))
            p.drawText(QRect(x, y, w, h), Qt.AlignCenter, "图片")
        elif kind == "table":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            cols = props.get("items", [])
            if cols:
                cw_ = w // len(cols)
                p.setFont(QFont("Microsoft YaHei UI", 9)); 
                f = p.font(); f.setBold(True); p.setFont(f)
                for i, c in enumerate(cols):
                    p.setBrush(QBrush(QColor("#f0eeea")))
                    p.setPen(QPen(QColor("#d8d6d1"), 1))
                    p.drawRect(x + i * cw_, y, cw_, 24)
                    p.setPen(QColor("#1c1917"))
                    p.drawText(QRect(x + i * cw_, y, cw_, 24), Qt.AlignCenter, str(c))
                p.setPen(QPen(QColor("#e8e6e2"), 1))
                for r in range(1, 4):
                    yy = y + 24 + r * 22
                    if yy > y + h: break
                    p.drawLine(x, yy, x + w, yy)
        elif kind == "panel":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor("#b0aea9"))
            p.drawText(QRect(x + 8, y + 4, w - 16, 20), Qt.AlignTop | Qt.AlignLeft, "面板")
        elif kind == "separator":
            p.setPen(QPen(QColor("#9c9a95"), 1))
            p.drawLine(x, y, x + w, y)
            if is_sel:
                p.setPen(QPen(QColor(C_SEL), 1))
                p.setBrush(Qt.NoBrush)
                p.drawRect(x, y - 3, w, 6)
        elif kind == "tabs":
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x, y, w, h)
            its = props.get("items", [])
            if its:
                tw = min(100, w // max(1, len(its)))
                p.setFont(QFont("Microsoft YaHei UI", 9))
                for i, t in enumerate(its):
                    tx = x + i * tw
                    p.setBrush(QBrush(QColor(C_CANVAS) if i == 0 else QColor("#f0eeea")))
                    p.setPen(QPen(QColor("#d8d6d1"), 1))
                    p.drawRect(tx, y, tw, 26)
                    p.setPen(QColor("#1c1917"))
                    p.drawText(QRect(tx, y, tw, 26), Qt.AlignCenter, str(t))

    def hit_test(self, x, y):
        for it in reversed(self.items):
            bx, by, bw, bh = comp_bbox(it)
            if bx <= x <= bx + bw and by <= y <= by + bh:
                return it
        return None

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        x, y = int(ev.x()), int(ev.y())
        it = self.hit_test(x, y)
        self.sel = it
        if it is not None:
            bx, by, _, _ = comp_bbox(it)
            self.drag_item = it
            self.drag_ox = x - bx
            self.drag_oy = y - by
        else:
            self.drag_item = None
        self.update()
        if self.parent():
            w = self.window()
            if hasattr(w, "refresh_props"):
                w.refresh_props()

    def mouseMoveEvent(self, ev):
        if self.drag_item is None:
            return
        x, y = int(ev.x()), int(ev.y())
        nx = x - self.drag_ox
        ny = y - self.drag_oy
        if self.grid:
            nx = (nx // 10) * 10
            ny = (ny // 10) * 10
        # 对齐吸附
        guides_x = [0]
        guides_y = [0]
        for other in self.items:
            if other is self.drag_item:
                continue
            ox, oy, ow, oh = comp_bbox(other)
            guides_x.extend([ox, ox + ow])
            guides_y.extend([oy, oy + oh])
        for g in guides_x:
            if abs(nx - g) <= 6:
                nx = g; break
        for g in guides_y:
            if abs(ny - g) <= 6:
                ny = g; break
        self.drag_item["props"]["x"] = max(0, nx)
        self.drag_item["props"]["y"] = max(0, ny)
        self.update()

    def mouseReleaseEvent(self, ev):
        if self.drag_item is not None:
            self.drag_item = None
            if self.parent():
                w = self.window()
                if hasattr(w, "refresh_props"):
                    w.refresh_props()

    def add_item(self, kind, x, y):
        m = hx()
        comp = m.UI_COMPONENTS_MAP[kind]
        d = dict(comp["defaults"])
        if self.grid:
            x = (x // 10) * 10
            y = (y // 10) * 10
        wid = self.next_id()
        props = {"id": wid, "x": max(0, x - d.get("w", 100) // 2), "y": max(0, y - d.get("h", 30) // 2)}
        props.update(d)
        it = {"id": wid, "kind": kind, "props": props}
        self.items.append(it)
        self.sel = it
        self.update()
        if self.parent():
            w = self.window()
            if hasattr(w, "refresh_props"):
                w.refresh_props()
        return it

    def next_id(self):
        used = set(it["id"] for it in self.items)
        n = 1
        while True:
            w = "w%d" % n
            if w not in used:
                return w
            n += 1


class PaletteList(QListWidget):
    """组件列表，支持拖出"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setStyleSheet("""
            QListWidget { background: #1c1f24; color: #d8dade; border: none; outline: none; }
            QListWidget::item { padding: 6px 14px; }
            QListWidget::item:hover { background: #2a2f36; }
            QListWidget::item:selected { background: #1e3a5c; color: #ffffff; }
        """)

    def startDrag(self, actions):
        it = self.currentItem()
        if it is None:
            return
        kind = it.data(Qt.UserRole)
        if not kind:
            return
        from PyQt5.QtCore import QMimeData
        from PyQt5.QtGui import QDrag
        mime = QMimeData()
        mime.setText("hx-ui:" + kind)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)


class DesignerDialog(QDialog):
    def __init__(self, parent=None, initial_items=None):
        super().__init__(parent)
        self.setWindowTitle("UI 设计器")
        self.resize(1240, 780)
        self.setStyleSheet(QSS)
        self.setMinimumSize(1000, 640)
        self.result_code = None
        self.prop_entries = {}

        m = hx()
        self.items = list(initial_items) if initial_items else []

        self._build_ui()
        self.canvas.items = self.items
        self.canvas.update()
        self.refresh_props()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶栏
        top = QFrame()
        top.setFixedHeight(44)
        top.setStyleSheet("QFrame{background:%s;border-bottom:1px solid %s;}" % (C_HEAD, C_BORDER))
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 6, 12, 6)
        t1 = QLabel("UI 设计器")
        f = QFont("Microsoft YaHei UI", 11); f.setBold(True)
        t1.setFont(f)
        t1.setStyleSheet("QLabel{color:%s;}" % C_TEXT)
        tl.addWidget(t1)
        t2 = QLabel("拖拽左侧组件到画布")
        t2.setStyleSheet("QLabel{color:%s;}" % C_MUTED)
        tl.addWidget(t2)
        tl.addStretch()
        self.btn_grid = QPushButton("网格 开")
        self.btn_grid.clicked.connect(self._toggle_grid)
        tl.addWidget(self.btn_grid)
        for text, slot, primary in [
            ("生成代码", self._do_generate, True),
            ("运行预览", self._do_preview, False),
            ("从编辑器导入", self._do_import, False),
            ("清空", self._do_clear, False),
        ]:
            b = QPushButton(text)
            if primary:
                b.setObjectName("primary")
            b.clicked.connect(slot)
            tl.addWidget(b)
        outer.addWidget(top)

        # 主体
        body = QFrame()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        # 左侧组件列表（按分组）
        left_wrap = QFrame()
        left_wrap.setFixedWidth(190)
        left_wrap.setStyleSheet("QFrame{background:%s;}" % C_PANEL)
        lv = QVBoxLayout(left_wrap)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        self.palette = PaletteList()
        lv.addWidget(self.palette, 1)
        self._fill_palette()
        bl.addWidget(left_wrap)

        bl.addWidget(self._vline())

        # 中间画布
        center_wrap = QFrame()
        center_wrap.setStyleSheet("QFrame{background:%s;}" % C_BG)
        cvl = QVBoxLayout(center_wrap)
        cvl.setContentsMargins(0, 0, 0, 0)
        cvl.setSpacing(0)
        chead = QFrame()
        chead.setFixedHeight(30)
        chead.setStyleSheet("QFrame{background:%s;border-bottom:1px solid %s;}" % (C_HEAD, C_BORDER))
        chl = QHBoxLayout(chead)
        chl.setContentsMargins(12, 0, 12, 0)
        lab = QLabel("画布")
        lab.setStyleSheet("QLabel{color:%s;}" % C_MUTED)
        chl.addWidget(lab)
        cvl.addWidget(chead)
        canvas_area = QWidget()
        cal = QVBoxLayout(canvas_area)
        cal.setContentsMargins(16, 16, 16, 16)
        self.canvas = CanvasWidget(canvas_area)
        self.canvas.setAcceptDrops(True)
        self.canvas.installEventFilter(self)
        cal.addWidget(self.canvas, 1)
        cvl.addWidget(canvas_area, 1)
        bl.addWidget(center_wrap, 1)

        bl.addWidget(self._vline())

        # 右侧属性
        right_wrap = QFrame()
        right_wrap.setFixedWidth(250)
        right_wrap.setStyleSheet("QFrame{background:%s;}" % C_PANEL)
        rv = QVBoxLayout(right_wrap)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rhead = QFrame()
        rhead.setFixedHeight(30)
        rhead.setStyleSheet("QFrame{background:%s;border-bottom:1px solid %s;}" % (C_HEAD, C_BORDER))
        rhl = QHBoxLayout(rhead)
        rhl.setContentsMargins(12, 0, 12, 0)
        rlab = QLabel("属性")
        rlab.setStyleSheet("QLabel{color:%s;}" % C_MUTED)
        rhl.addWidget(rlab)
        rv.addWidget(rhead)
        self.prop_scroll = QScrollArea()
        self.prop_scroll.setWidgetResizable(True)
        self.prop_inner = QWidget()
        self.prop_layout = QVBoxLayout(self.prop_inner)
        self.prop_layout.setContentsMargins(12, 12, 12, 12)
        self.prop_layout.setSpacing(6)
        self.prop_scroll.setWidget(self.prop_inner)
        rv.addWidget(self.prop_scroll, 1)
        bl.addWidget(right_wrap)

        outer.addWidget(body, 1)

        # 状态栏
        sb = QFrame()
        sb.setFixedHeight(24)
        sb.setStyleSheet("QFrame{background:%s;border-top:1px solid %s;}" % (C_HEAD, C_BORDER))
        sl = QHBoxLayout(sb)
        sl.setContentsMargins(14, 0, 14, 0)
        self.status = QLabel("就绪")
        self.status.setStyleSheet("QLabel{color:%s;font-size:8pt;}" % C_MUTED)
        sl.addWidget(self.status)
        outer.addWidget(sb)

    def _vline(self):
        f = QFrame()
        f.setFixedWidth(1)
        f.setStyleSheet("QFrame{background:%s;}" % C_BORDER)
        return f

    def _fill_palette(self):
        from PyQt5.QtWidgets import QListWidgetItem
        m = hx()
        last_group = None
        for comp in m.UI_COMPONENTS:
            g = comp["group"]
            if g != last_group:
                hdr = QListWidgetItem(g)
                hdr.setFlags(Qt.NoItemFlags)
                hdr.setForeground(QColor(C_MUTED))
                fh = QFont("Microsoft YaHei UI", 8); fh.setBold(True)
                hdr.setFont(fh)
                self.palette.addItem(hdr)
                last_group = g
            it = QListWidgetItem(comp["label"])
            it.setData(Qt.UserRole, comp["kind"])
            self.palette.addItem(it)

    def _toggle_grid(self):
        self.canvas.grid = not self.canvas.grid
        self.btn_grid.setText("网格 开" if self.canvas.grid else "网格 关")
        self.canvas.update()

    def eventFilter(self, obj, ev):
        if obj is self.canvas:
            if ev.type() == ev.DragEnter:
                if ev.mimeData().hasText() and ev.mimeData().text().startswith("hx-ui:"):
                    ev.acceptProposedAction()
                    return True
            elif ev.type() == ev.Drop:
                txt = ev.mimeData().text()
                if txt.startswith("hx-ui:"):
                    kind = txt[len("hx-ui:"):]
                    pos = ev.pos()
                    self.canvas.add_item(kind, pos.x(), pos.y())
                    ev.acceptProposedAction()
                    return True
        return super().eventFilter(obj, ev)

    def refresh_props(self):
        # 清空
        while self.prop_layout.count():
            item = self.prop_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.prop_entries.clear()

        sel = self.canvas.sel
        if sel is None:
            lab = QLabel("在画布中选中组件\n即可在这里编辑属性")
            lab.setStyleSheet("QLabel{color:%s;}" % C_MUTED)
            self.prop_layout.addWidget(lab)
            self.prop_layout.addStretch()
            return

        m = hx()
        kind = sel["kind"]
        p = sel["props"]
        comp = m.UI_COMPONENTS_MAP[kind]

        t = QLabel(comp["label"])
        f = QFont("Microsoft YaHei UI", 10); f.setBold(True)
        t.setFont(f)
        t.setStyleSheet("QLabel{color:%s;}" % C_TEXT)
        self.prop_layout.addWidget(t)

        t2 = QLabel(p["id"])
        t2.setStyleSheet("QLabel{color:%s;font-family:Consolas;}" % C_MUTED)
        self.prop_layout.addWidget(t2)
        self.prop_layout.addSpacing(6)

        for field in comp["fields"]:
            lab = QLabel(FIELD_LABELS.get(field, field))
            lab.setStyleSheet("QLabel{color:%s;font-size:8pt;}" % C_MUTED)
            self.prop_layout.addWidget(lab)
            e = QLineEdit()
            v = p.get(field, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            e.setText(str(v))
            e.textChanged.connect(self._apply_props)
            self.prop_layout.addWidget(e)
            self.prop_entries[field] = e

        self.prop_layout.addSpacing(10)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("QFrame{background:%s;}" % C_BORDER)
        self.prop_layout.addWidget(line)

        btn = QPushButton("删除组件")
        btn.setStyleSheet("QPushButton{background:#3a2020;color:#e07070;border:none;border-radius:3px;padding:6px;}")
        btn.clicked.connect(self._delete_selected)
        self.prop_layout.addWidget(btn)
        self.prop_layout.addStretch()

    def _apply_props(self):
        sel = self.canvas.sel
        if sel is None:
            return
        p = sel["props"]
        old_id = p.get("id", "")
        for field, e in self.prop_entries.items():
            v = e.text()
            if field in NUM_FIELDS:
                try:
                    p[field] = int(float(v))
                except Exception:
                    pass
            elif field == "items":
                p[field] = [s.strip() for s in v.split(",") if s.strip()]
            else:
                p[field] = v
        if p.get("id") != old_id:
            sel["id"] = p["id"]
        self.canvas.update()

    def _delete_selected(self):
        sel = self.canvas.sel
        if sel is None:
            return
        if sel in self.items:
            self.items.remove(sel)
        self.canvas.sel = None
        self.canvas.update()
        self.refresh_props()
        self.status.setText("已删除组件")

    def _do_generate(self):
        m = hx()
        code = m.ui_gen_code(self.items)
        self.result_code = code
        self.status.setText("已生成代码（%d 个组件）" % len(self.items))
        QMessageBox.information(self, "生成完成", "代码已准备好，点击确定后插入编辑器。")
        self.accept()

    def _do_preview(self):
        if not self.items:
            QMessageBox.information(self, "提示", "还没有添加组件")
            return
        m = hx()
        code = m.ui_gen_code(self.items)
        p = os.path.join(tempfile.gettempdir(), "_ui_preview.hxg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            subprocess.Popen([sys.executable, os.path.abspath(m.__file__), p])
        except Exception as e:
            QMessageBox.warning(self, "预览失败", str(e))

    def _do_import(self):
        QMessageBox.information(self, "提示", "从编辑器导入请在 IDE 里打开设计器前操作（会读取当前代码）。")

    def _do_clear(self):
        if not self.items:
            return
        r = QMessageBox.question(self, "清空画布", "确定要清空所有组件吗？",
                                 QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self.items.clear()
            self.canvas.sel = None
            self.canvas.update()
            self.refresh_props()
            self.status.setText("画布已清空")

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Delete:
            self._delete_selected()
            return
        super().keyPressEvent(ev)


def open_designer(initial_items=None, parent=None):
    app = QApplication.instance()
    own = False
    if app is None:
        app = QApplication(sys.argv if sys.argv else [""])
        own = True
    dlg = DesignerDialog(parent, initial_items=initial_items)
    dlg.exec_()
    return dlg.result_code


if __name__ == "__main__":
    code = open_designer()
    if code:
        print(code)
