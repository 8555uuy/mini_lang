# MiniLang v2 —— 解释器 + 编码器
# 语法：x = 1;  f(a,b){...}  if/else if/else  while  for  return
#       print("hi", 1);  数组 [1,2]  字典 {a:1}  字符串 "x" 或 'x'  注释 #
import sys, re, os, math, json, threading, queue, time, subprocess, webbrowser
import urllib.request, urllib.error, urllib.parse
import concurrent.futures, zipfile, hashlib

KEYWORDS = {"let","if","else","elif","while","for","break","continue","del",
            "return","true","false","null","and","or","not","try","catch"}
OPS = ["==","!=","<=",">=","+=","-=","*=","/=","%=","&&","||","+","-","*","/","%","<",">","=",
       "(",")","{","}","[","]",",",";",":",".","!"]

class MiniError(Exception):
    pass

class Tok:
    __slots__ = ("k","v","line","col")
    def __init__(self,k,v,line,col):
        self.k=k; self.v=v; self.line=line; self.col=col


def tokenize(src):
    toks=[]; i=0; n=len(src); line=1; col=1
    while i<n:
        c=src[i]
        if c in " \t\r\n":
            if c=="\n": line+=1; col=1
            else: col+=1
            i+=1; continue
        if c=="#":
            while i<n and src[i]!="\n": i+=1
            continue
        l0,c0=line,col
        if c.isdigit():
            j=i
            while j<n and (src[j].isdigit() or src[j]=="."): j+=1
            toks.append(Tok("num",float(src[i:j]),l0,c0)); col+=j-i; i=j; continue
        if c.isalpha() or c=="_":
            j=i
            while j<n and (src[j].isalnum() or src[j]=="_"): j+=1
            w=src[i:j]; col+=j-i; i=j
            toks.append(Tok(w,w,l0,c0) if w in KEYWORDS else Tok("id",w,l0,c0)); continue
        if c in "\"'":
            q=c; i+=1; col+=1; buf=[]; depth=0
            while i<n:
                ch=src[i]
                if ch=="\\" and i+1<n and depth==0:
                    i+=1; e=src[i]; i+=1; col+=2
                    buf.append({"n":"\n","t":"\t"}.get(e,e)); continue
                if depth==0 and ch==q: break
                if src.startswith("${",i):
                    depth+=1; buf.append("${"); i+=2; col+=2; continue
                if ch=="}" and depth>0:
                    depth-=1; buf.append("}"); i+=1; col+=1; continue
                if ch=="\n": line+=1; col=1
                else: col+=1
                buf.append(ch); i+=1
            if i>=n: raise SyntaxError("第 %d 行第 %d 列：字符串未闭合" % (l0,c0))
            i+=1; col+=1
            toks.append(Tok("str","".join(buf),l0,c0)); continue
        for op in OPS:
            if src.startswith(op,i):
                toks.append(Tok(op,op,l0,c0)); i+=len(op); col+=len(op); break
        else:
            raise SyntaxError("第 %d 行第 %d 列：未知字符 %r" % (l0,c0,c))
    toks.append(Tok("eof","eof",line,col))
    return toks


class Parser:
    def __init__(self,toks):
        self.t=toks; self.p=0

    def peek(self,k=0):
        return self.t[min(self.p+k,len(self.t)-1)]

    def at(self,*ks):
        return self.peek().k in ks

    def take(self,k=None):
        t=self.peek()
        if k is not None and t.k!=k:
            raise SyntaxError("第 %d 行第 %d 列：期望 %r，得到 %r" % (t.line,t.col,k,t.k))
        self.p+=1; return t

    def eat(self,k):
        if self.at(k):
            self.p+=1; return True
        return False

    def end(self):
        self.eat(";")

    def program(self):
        body=[]
        while not self.at("eof"): body.append(self.stmt())
        return ("block",body,1)

    def _is_fn_def(self):
        if self.peek().k!="id" or self.peek(1).k!="(":
            return False
        depth=0; i=1
        while True:
            t=self.peek(i)
            if t.k=="eof": return False
            if t.k=="(": depth+=1
            elif t.k==")":
                depth-=1
                if depth==0: return self.peek(i+1).k=="{"
            i+=1

    def block(self):
        t=self.take("{")
        body=[]
        while not self.at("}"):
            if self.at("eof"): raise SyntaxError("第 %d 行：缺少 '}'" % t.line)
            body.append(self.stmt())
        self.take("}")
        return ("block",body,t.line)

    def stmt(self):
        t=self.peek(); line=t.line
        if t.k=="let":
            raise SyntaxError("第 %d 行：let 声明已废弃，请直接写 x = 1;（自动判断类型）" % line)
        if t.k=="id" and t.v=="print" and self.peek(1).k!="(":
            raise SyntaxError("第 %d 行：print 必须加括号，写成 print(...)" % line)
        if t.k=="id" and t.v=="scanf":
            self.take(); self.take("(")
            fmt_node=self.expr(); self.take(",")
            names=[]
            while not self.at(")"):
                names.append(self.take("id").v)
                if not self.eat(","): break
            self.take(")")
            self.end()
            return ("scanf",fmt_node,names,line)
        if t.k=="id" and t.v=="fn":
            raise SyntaxError("第 %d 行：没有 fn 关键字，直接写 名字(参数) { ... }" % line)
        if self._is_fn_def():
            name=self.take("id").v; self.take("("); ps=[]
            while not self.at(")"):
                ps.append(self.take("id").v)
                if not self.eat(","): break
            self.take(")")
            return ("func",name,ps,self.block(),line)
        if self.eat("return"):
            e=None if self.at("}",";","eof") else self.expr()
            self.end()
            return ("return",e,line)
        if self.eat("if"):
            self.take("("); c=self.expr(); self.take(")")
            then=self.stmt()
            els=self.stmt() if self.eat("else") else None
            return ("if",c,then,els,line)
        if self.at("elif"):
            raise SyntaxError("第 %d 行：没有 elif，请改用 else if" % line)
        if self.eat("try"):
            body=self.stmt()
            self.take("catch"); self.take("("); nm=self.take("id").v; self.take(")")
            handler=self.stmt()
            return ("try",body,nm,handler,line)
        if self.eat("while"):
            self.take("("); c=self.expr(); self.take(")")
            return ("while",c,self.stmt(),line)
        if self.eat("for"):
            if self.at("id") and self.peek(1).k=="in":
                raise SyntaxError("第 %d 行：不支持 for (x in arr)，请用 for (i = 0; i < len(arr); i += 1)" % line)
            self.take("(")
            init=None if self.at(";") else self.expr()
            self.take(";")
            cond=None if self.at(";") else self.expr()
            self.take(";")
            step=None if self.at(")") else self.expr()
            self.take(")")
            return ("forc",init,cond,step,self.stmt(),line)
        if self.eat("break"):
            self.end(); return ("break",line)
        if self.eat("continue"):
            self.end(); return ("continue",line)
        if self.eat("del"):
            tgt=self.postfix(); self.end()
            return ("del",tgt,line)
        if self.at("{"): return self.block()
        e=self.expr(); self.end()
        return ("expr",e,line)

    def expr(self): return self.assign()

    def assign(self):
        node=self.or_()
        t=self.peek()
        if t.k=="=":
            self.take()
            return ("set",node,self.assign(),node[-1])
        if t.k in ("+=","-=","*=","/=","%="):
            op=self.take().k[:-1]
            return ("set",node,("bin",op,node,self.assign(),node[-1]),node[-1])
        return node

    def or_(self):
        node=self.and_()
        while self.eat("or") or self.eat("||"):
            node=("bin","or",node,self.and_(),node[-1])
        return node

    def and_(self):
        node=self.not_()
        while self.eat("and") or self.eat("&&"):
            node=("bin","and",node,self.not_(),node[-1])
        return node

    def not_(self):
        if self.at("not","!"):
            line=self.take().line
            return ("un","not",self.not_(),line)
        return self.cmp()

    def cmp(self):
        node=self.add()
        while self.at("==","!=","<","<=",">",">="):
            op=self.take().k
            node=("bin",op,node,self.add(),node[-1])
        return node

    def add(self):
        node=self.mul()
        while self.at("+","-"):
            op=self.take().k
            node=("bin",op,node,self.mul(),node[-1])
        return node

    def mul(self):
        node=self.unary()
        while self.at("*","/","%"):
            op=self.take().k
            node=("bin",op,node,self.unary(),node[-1])
        return node

    def unary(self):
        if self.at("-"):
            line=self.take().line
            return ("un","-",self.unary(),line)
        return self.postfix()

    def postfix(self):
        node=self.atom()
        while True:
            if self.eat("("):
                args=[]
                while not self.at(")"):
                    args.append(self.expr())
                    if not self.eat(","): break
                self.take(")")
                node=("call",node,args,node[-1])
            elif self.eat("["):
                idx=self.expr(); self.take("]")
                node=("idx",node,idx,node[-1])
            elif self.eat("."):
                name=self.take("id").v
                node=("attr",node,name,node[-1])
            else:
                return node

    def atom(self):
        t=self.peek()
        if t.k=="let":
            raise SyntaxError("第 %d 行：let 声明已废弃，请直接写 x = 1;（自动判断类型）" % t.line)
        if t.k=="num": self.take(); return ("num",t.v,t.line)
        if t.k=="str":
            self.take()
            if "${" not in t.v: return ("str",t.v,t.line)
            parts=[]; s=t.v; i=0
            while True:
                j=s.find("${",i)
                if j<0: parts.append(("str",s[i:],t.line)); break
                if j>i: parts.append(("str",s[i:j],t.line))
                k2=s.find("}",j)
                if k2<0: raise SyntaxError("第 %d 行：插值未闭合" % t.line)
                parts.append(Parser(tokenize(s[j+2:k2])).expr())
                i=k2+1
            return ("cat",parts,t.line)
        if t.k=="true": self.take(); return ("bool",True,t.line)
        if t.k=="false": self.take(); return ("bool",False,t.line)
        if t.k=="null": self.take(); return ("null",None,t.line)
        if t.k=="id" and t.v=="dar":
            raise SyntaxError("第 %d 行：dar 已改名为 type，请用 type(x) 查询类型" % t.line)
        if t.k=="id":
            self.take(); return ("id",t.v,t.line)
        if t.k=="(":
            self.take(); e=self.expr(); self.take(")"); return e
        if t.k=="[":
            self.take(); items=[]
            while not self.at("]"):
                items.append(self.expr())
                if not self.eat(","): break
            self.take("]")
            return ("list",items,t.line)
        if t.k=="{":
            self.take(); pairs=[]
            while not self.at("}"):
                kt=self.take()
                if kt.k not in ("str","id","num"):
                    raise SyntaxError("第 %d 行：字典键必须是字符串或标识符" % kt.line)
                self.take(":")
                pairs.append((kt.v,self.expr()))
                if not self.eat(","): break
            self.take("}")
            return ("dict",pairs,t.line)
        raise SyntaxError("第 %d 行第 %d 列：意外的 %r" % (t.line,t.col,t.k))


class Env:
    def __init__(self,parent=None):
        self.vars={}; self.parent=parent

    def get(self,k):
        e=self
        while e:
            if k in e.vars: return e.vars[k]
            e=e.parent
        raise NameError("未定义的变量 %s" % k)

    def set(self,k,v):
        e=self
        while e:
            if k in e.vars:
                e.vars[k]=v; return
            e=e.parent
        raise NameError("未定义的变量 %s" % k)

    def define(self,k,v):
        self.vars[k]=v


class Fn:
    def __init__(self,params,body,env,name):
        self.params=params; self.body=body; self.env=env; self.name=name


class Native:
    def __init__(self,fn): self.fn=fn


# 哨兵：表示后台任务没有返回值，回调应收到空参数表
_BG_NO_RESULT = object()


# ===== Qt 全局单例 =====
_QT_APP = None

def _qt_app():
    """获取或创建全局 QApplication 单例（Qt 只允许一个）"""
    global _QT_APP
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        _QT_APP = QApplication(sys.argv if sys.argv else [""])
        app = _QT_APP
    else:
        _QT_APP = app
    return app


# PCL2 风格的全局 QSS：圆角、柔和边框、蓝色强调
_UI_QSS = """
QWidget { background:#fafaf9; font-family:'Microsoft YaHei UI'; font-size:10pt; color:#1c1917; }
QPushButton {
    background:#ffffff; border:1px solid #d8d5d0; border-radius:6px;
    padding:4px 12px;
}
QPushButton:hover { background:#f4f3f0; border-color:#2f7fd8; }
QPushButton:pressed { background:#e8e6e2; }
QPushButton:disabled { color:#a8a5a0; }
QLineEdit, QTextEdit, QComboBox, QTableWidget {
    background:#ffffff; border:1px solid #d8d5d0; border-radius:6px;
    padding:4px 8px;
}
QLineEdit:focus, QTextEdit:focus { border-color:#2f7fd8; }
QComboBox::drop-down { border:none; width:20px; }
QListWidget {
    background:#ffffff; border:1px solid #d8d5d0; border-radius:6px;
}
QListWidget::item { padding:4px 8px; }
QListWidget::item:selected { background:#e0efff; color:#1c1917; }
QTabWidget::pane {
    border:1px solid #d8d5d0; border-radius:6px; background:#ffffff; top:-1px;
}
QTabBar::tab {
    background:#f4f3f0; border:1px solid #d8d5d0; border-bottom:none;
    border-top-left-radius:6px; border-top-right-radius:6px;
    padding:6px 14px; margin-right:2px;
}
QTabBar::tab:selected { background:#ffffff; color:#1c1917; }
QProgressBar { background:#e8e6e2; border:none; border-radius:4px; }
QProgressBar::chunk { background:#2f7fd8; border-radius:4px; }
QSlider::groove:horizontal { background:#e8e6e2; height:4px; border-radius:2px; }
QSlider::handle:horizontal {
    background:#2f7fd8; width:14px; height:14px; margin:-5px 0;
    border-radius:7px;
}
QHeaderView::section {
    background:#f4f3f0; border:none; border-bottom:1px solid #d8d5d0;
    padding:4px 8px;
}
QCheckBox, QRadioButton { spacing:6px; }
QCheckBox::indicator, QRadioButton::indicator { width:14px; height:14px; }
"""


class Return(Exception):
    def __init__(self,value): self.value=value

class BreakSig(Exception): pass
class ContinueSig(Exception): pass


def truth(v):
    if v is None or v is False: return False
    if isinstance(v,bool): return v
    if isinstance(v,(int,float)): return v!=0
    if isinstance(v,(str,list,dict)): return len(v)>0
    return True


def typename(v):
    if isinstance(v,bool): return "布尔"
    if isinstance(v,(int,float)): return "数字"
    if isinstance(v,str): return "字符串"
    if isinstance(v,list): return "数组"
    if isinstance(v,dict): return "字典"
    if isinstance(v,(Fn,Native)): return "函数"
    if v is None: return "空"
    return "未知"


def fmt(v):
    if v is True: return "true"
    if v is False: return "false"
    if v is None: return "null"
    if isinstance(v,float) and v.is_integer(): return str(int(v))
    if isinstance(v,list): return "["+", ".join(fmt(x) for x in v)+"]"
    if isinstance(v,dict): return "{"+", ".join("%s: %s"%(k,fmt(x)) for k,x in v.items())+"}"
    if isinstance(v,(Fn,Native)): return "<fn>"
    return str(v)


def to_num(v):
    if isinstance(v,(int,float)): return float(v)
    try: return float(v)
    except Exception: raise MiniError("不能转成数字：%s" % fmt(v))


class Interp:
    def __init__(self, root=None):
        self.globals=Env(); self.env=self.globals
        self.outbuf=[]; self.steps=0; self.maxsteps=300000; self.trace=[]; self.ask_fn=None
        self.root=root; self.gwin=None; self.gcanvas=None; self._owns_gwin=False
        self._wait_key=None; self._wait_click=None; self._cb_errors=[]
        self.ui_win_obj=None; self.ui_widgets={}; self.ui_handlers={}; self.ui_running=False
        # ===== 后台任务设施 =====
        # 线程池：IO/计算在后台线程跑，不阻塞主线程
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="hx-bg")
        # 后台完成后的回调队列：元素为 (回调函数, 结果, 异常)，只在主线程 poll_bg_tasks 里取
        self._bg_queue = queue.Queue()
        # 后台任务句柄表：id -> Future（供 bg_status / bg_wait 查询）
        self._bg_futures = {}
        self._bg_next_id = 1
        g=self.globals
        g.define("type",Native(lambda a: typename(a[0])))
        g.define("help",Native(lambda a: self.out(cheatsheet_text()+"\n")))
        g.define("has",Native(lambda a: (a[1] in a[0]) if isinstance(a[0],(dict,list,str)) else False))
        g.define("set",Native(lambda a: (a[0].__setitem__(a[1],a[2]),a[0])[1]))
        g.define("items",Native(lambda a: [[k,v] for k,v in a[0].items()]))
        g.define("upper",Native(lambda a: fmt(a[0]).upper()))
        g.define("lower",Native(lambda a: fmt(a[0]).lower()))
        g.define("trim",Native(lambda a: fmt(a[0]).strip()))
        g.define("split",Native(lambda a: fmt(a[0]).split(fmt(a[1])) if len(a)>1 else fmt(a[0]).split()))
        g.define("join",Native(lambda a: fmt(a[0]).join(fmt(x) for x in a[1])))
        g.define("min",Native(lambda a: min(a[0]) if len(a)==1 and isinstance(a[0],list) else min(a)))
        g.define("max",Native(lambda a: max(a[0]) if len(a)==1 and isinstance(a[0],list) else max(a)))
        g.define("abs",Native(lambda a: abs(a[0])))
        g.define("sqrt",Native(lambda a: math.sqrt(a[0])))
        g.define("sin",Native(lambda a: math.sin(a[0])))
        g.define("cos",Native(lambda a: math.cos(a[0])))
        g.define("tan",Native(lambda a: math.tan(a[0])))
        g.define("floor",Native(lambda a: float(math.floor(a[0]))))
        g.define("ceil",Native(lambda a: float(math.ceil(a[0]))))
        g.define("round",Native(lambda a: float(round(a[0]))))
        g.define("random",Native(lambda a: __import__("random").random()))
        g.define("PI",3.141592653589793)
        g.define("input",Native(lambda a: (self.out(fmt(a[0])) if a else None, self.ask())[1]))
        g.define("print",Native(lambda a: self.out(" ".join(fmt(x) for x in a)+"\n")))
        g.define("len",Native(lambda a: len(a[0])))
        g.define("push",Native(lambda a: (a[0].append(a[1]),a[0])[1]))
        g.define("keys",Native(lambda a: list(a[0].keys())))
        g.define("str",Native(lambda a: fmt(a[0])))
        g.define("num",Native(lambda a: to_num(a[0])))
        g.define("range",Native(lambda a: [float(x) for x in range(int(a[0]))]))
        g.define("gwin",Native(self.g_win))
        g.define("gline",Native(self.g_line))
        g.define("grect",Native(self.g_rect))
        g.define("gcircle",Native(self.g_circle))
        g.define("gtext",Native(self.g_text))
        g.define("gclear",Native(self.g_clear))
        g.define("gsleep",Native(self.g_sleep))
        g.define("gwaitkey",Native(self.g_waitkey))
        g.define("gwaitclick",Native(self.g_waitclick))
        g.define("gkeydown",Native(self.g_keydown))
        g.define("gclick",Native(self.g_click))
        g.define("readfile",Native(self.f_readfile))
        g.define("writefile",Native(self.f_writefile))
        g.define("appendfile",Native(self.f_appendfile))
        g.define("exists",Native(self.f_exists))
        g.define("files",Native(self.f_files))
        g.define("openfile",Native(self.f_openfile))
        g.define("openurl",Native(self.f_openurl))
        g.define("runapp",Native(self.f_runapp))
        g.define("http_get",Native(self.h_http_get))
        g.define("http_download",Native(self.h_http_download))
        g.define("md5",Native(self.h_md5))
        g.define("sha256",Native(self.h_sha256))
        g.define("unzip",Native(self.h_unzip))
        g.define("zipinfo",Native(self.h_zipinfo))
        g.define("bg_run",Native(self.h_bg_run))
        g.define("uiwin",Native(self.ui_win))
        g.define("uibtn",Native(self.ui_btn))
        g.define("uilabel",Native(self.ui_label))
        g.define("uiheading",Native(self.ui_heading))
        g.define("uiinput",Native(self.ui_input))
        g.define("uitext",Native(self.ui_text))
        g.define("uicheck",Native(self.ui_check))
        g.define("uiradio",Native(self.ui_radio))
        g.define("uicombo",Native(self.ui_combo))
        g.define("uilist",Native(self.ui_list))
        g.define("uirange",Native(self.ui_range))
        g.define("uiprogress",Native(self.ui_progress))
        g.define("uiimage",Native(self.ui_image))
        g.define("uitable",Native(self.ui_table))
        g.define("uipanel",Native(self.ui_panel))
        g.define("uiseparator",Native(self.ui_separator))
        g.define("uitabs",Native(self.ui_tabs))
        g.define("uion",Native(self.ui_on))
        g.define("uiget",Native(self.ui_get))
        g.define("uiset",Native(self.ui_set))
        g.define("uirun",Native(self.ui_run))

    def ask(self):
        if self.ask_fn: return self.ask_fn()
        try: return input()
        except Exception: return ""

    def _read_line(self, prompt):
        if prompt:
            self.out(prompt)
        return self.ask()

    def do_scanf(self, fmt_node, names, line):
        fmt = fmt_node[1] if fmt_node[0] == "str" else fmt(fmt_node)
        # 拆分格式串：每遇到一个 %d/%f/%s/%c 就是一次读取
        specs = []
        i = 0
        n = len(fmt)
        while i < n:
            if fmt[i] == "%" and i + 1 < n:
                t = fmt[i+1]
                if t in "dfsc":
                    specs.append(t)
                    i += 2
                    continue
                if t == "%":
                    i += 2
                    continue
            i += 1
        if not specs:
            raise MiniError("第 %d 行：scanf 的格式串里没有 %%d/%%f/%%s/%%c" % line)
        if len(specs) != len(names):
            raise MiniError("第 %d 行：scanf 格式串有 %d 个占位符，但给了 %d 个变量"
                            % (line, len(specs), len(names)))
        # 检查变量都已声明
        for nm in names:
            try:
                self.env.get(nm)
            except NameError:
                raise MiniError("第 %d 行：scanf 的变量 %s 未声明，请先写 %s = 0;" % (line, nm, nm))
        # 读取：优先用一次输入切分，若字段不够则继续读
        values = []
        prompt_shown = False
        while len(values) < len(specs):
            prompt = ""
            if not prompt_shown:
                prompt = ""
                prompt_shown = True
            raw = self._read_line(prompt)
            parts = raw.split()
            for p in parts:
                if len(values) >= len(specs):
                    break
                values.append(p)
            if not parts and len(values) < len(specs):
                continue
        # 按类型转换并赋值
        for idx, nm in enumerate(names):
            spec = specs[idx]
            v = values[idx]
            if spec == "d":
                try:
                    iv = int(float(v))
                except Exception:
                    raise MiniError("第 %d 行：scanf 需要整数，得到 \"%s\"" % (line, v))
                self.env.set(nm, float(iv))
            elif spec == "f":
                try:
                    self.env.set(nm, float(v))
                except Exception:
                    raise MiniError("第 %d 行：scanf 需要数字，得到 \"%s\"" % (line, v))
            elif spec == "c":
                self.env.set(nm, v[0] if v else "")
            else:
                self.env.set(nm, v)
        return None

    def text(self): return "".join(self.outbuf)
    def out(self,s): self.outbuf.append(s)

    def _g_num(self, v, fname, pname):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise MiniError(f"{fname} 的 {pname} 必须是数字，得到：{fmt(v)}")
        return float(v)

    def _g_color(self, v, fname, pname):
        if not isinstance(v, str):
            raise MiniError(f"{fname} 的 {pname} 必须是字符串，得到：{fmt(v)}")
        return v

    def g_win(self, args):
        import tkinter as tk
        if len(args) < 2:
            raise MiniError('gwin 需要至少 2 个参数：宽, 高。例如 gwin(600, 400, "我的画板")')
        w = int(self._g_num(args[0], "gwin", "宽"))
        h = int(self._g_num(args[1], "gwin", "高"))
        title = str(args[2]) if len(args) > 2 else "HX 图形窗口"
        if w <= 0 or h <= 0:
            raise MiniError("gwin 的宽和高必须大于 0")
        
        if self.gwin is not None:
            try: self.gwin.destroy()
            except Exception: pass
        
        try:
            if self.root is not None:
                self.gwin = tk.Toplevel(self.root)
            else:
                self.gwin = tk.Tk()
                self._owns_gwin = True
            self.gwin.title(title)
            self.gwin.configure(bg="white")
            self.gwin.geometry("%dx%d"%(w,h))
            self.gcanvas = tk.Canvas(self.gwin,width=w,height=h,bg="white",highlightthickness=0,takefocus=1)
            self.gcanvas.pack(fill="both",expand=True)
            self.gwin.update()
        except Exception as e:
            raise MiniError(f"创建图形窗口失败：{e}")
        return None

    def g_canvas(self):
        if self.gcanvas is None:
            raise MiniError("请先调用 gwin(宽, 高) 创建图形窗口，再进行绘制")
        return self.gcanvas

    def g_line(self, args):
        if len(args) < 4:
            raise MiniError("gline 需要至少 4 个参数：(x1, y1, x2, y2, color, width)")
        c = self.g_canvas()
        x1=self._g_num(args[0],"gline","x1"); y1=self._g_num(args[1],"gline","y1")
        x2=self._g_num(args[2],"gline","x2"); y2=self._g_num(args[3],"gline","y2")
        color=self._g_color(args[4],"gline","color") if len(args)>4 else "black"
        width=self._g_num(args[5],"gline","width") if len(args)>5 else 2
        try: return c.create_line(x1,y1,x2,y2,fill=color,width=width)
        except Exception as e: raise MiniError(f"gline 绘制失败（颜色名是否正确？）：{e}")

    def g_rect(self, args):
        if len(args) < 4:
            raise MiniError("grect 需要至少 4 个参数：(x1, y1, x2, y2, color, fill)")
        c = self.g_canvas()
        x1=self._g_num(args[0],"grect","x1"); y1=self._g_num(args[1],"grect","y1")
        x2=self._g_num(args[2],"grect","x2"); y2=self._g_num(args[3],"grect","y2")
        color=self._g_color(args[4],"grect","color") if len(args)>4 else "black"
        fill=self._g_color(args[5],"grect","fill") if len(args)>5 else ""
        try: return c.create_rectangle(x1,y1,x2,y2,outline=color,fill=fill)
        except Exception as e: raise MiniError(f"grect 绘制失败（颜色名是否正确？）：{e}")

    def g_circle(self, args):
        if len(args) < 3:
            raise MiniError("gcircle 需要至少 3 个参数：(cx, cy, r, color, fill)")
        c = self.g_canvas()
        cx=self._g_num(args[0],"gcircle","cx"); cy=self._g_num(args[1],"gcircle","cy")
        r=self._g_num(args[2],"gcircle","r")
        if r < 0: raise MiniError("gcircle 的半径 r 不能为负数")
        color=self._g_color(args[3],"gcircle","color") if len(args)>3 else "black"
        fill=self._g_color(args[4],"gcircle","fill") if len(args)>4 else ""
        try: return c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=color,fill=fill)
        except Exception as e: raise MiniError(f"gcircle 绘制失败（颜色名是否正确？）：{e}")

    def g_text(self, args):
        if len(args) < 3:
            raise MiniError("gtext 需要至少 3 个参数：(x, y, text, color)")
        c = self.g_canvas()
        x=self._g_num(args[0],"gtext","x"); y=self._g_num(args[1],"gtext","y")
        text=fmt(args[2])
        color=self._g_color(args[3],"gtext","color") if len(args)>3 else "black"
        try: return c.create_text(x,y,text=text,fill=color,font=("Microsoft YaHei UI",12))
        except Exception as e: raise MiniError(f"gtext 绘制失败：{e}")

    def g_clear(self, args):
        self.g_canvas().delete("all")
        return None

    def g_sleep(self, args):
        ms = int(self._g_num(args[0],"gsleep","毫秒数")) if args else 10
        remain = max(0, ms) / 1000.0
        try:
            if self.gwin is not None: self.gwin.update()
            # 分片 sleep，每片处理一次后台回调，保证响应性
            end = time.time() + remain
            while True:
                self.poll_bg_tasks()
                left = end - time.time()
                if left <= 0: break
                time.sleep(min(left, 0.016))
                if self.gwin is not None: self.gwin.update()
            if self.gwin is not None: self.gwin.update()
        except MiniError:
            raise
        except Exception:
            if remain > 0: time.sleep(remain)
        self._check_cb_errors()
        return None

    def _key_name(self, e):
        k = e.keysym
        if k == "space": return "space"
        if k == "Return": return "enter"
        if k == "Escape": return "esc"
        if k == "BackSpace": return "backspace"
        if k == "Tab": return "tab"
        if len(k) == 1 and e.state & 0x1:
            return k.lower()
        return k if len(k) > 1 else k.lower()

    def _check_cb_errors(self):
        if self._cb_errors:
            msg = self._cb_errors[0]
            self._cb_errors.clear()
            raise MiniError(msg)

    # ===== 后台任务泵 =====
    def poll_bg_tasks(self):
        """主线程每帧调用：把已完成的后台回调搬运到主线程执行。
        回调里可以安全操作 UI（因为就在这里的主线程执行）。"""
        while True:
            try:
                cb, result, err = self._bg_queue.get_nowait()
            except queue.Empty:
                break
            if err is not None:
                self._cb_errors.append(str(err))
                continue
            if cb is None:
                continue
            try:
                self.call(cb, [result] if result is not _BG_NO_RESULT else [], 0)
            except Exception as ex:
                self._cb_errors.append(str(ex))
        self._check_cb_errors()

    def _submit_bg(self, fn, done_cb=None):
        """把 fn 丢进线程池；完成后把 (done_cb, 结果, 异常) 放进队列，由主线程执行 done_cb。"""
        def worker():
            try:
                r = fn()
                self._bg_queue.put((done_cb, r, None))
            except Exception as e:
                self._bg_queue.put((done_cb, None, e))
        fut = self._pool.submit(worker)
        bid = self._bg_next_id
        self._bg_next_id += 1
        self._bg_futures[bid] = fut
        # 清理已完成的句柄
        for k in [k for k, f in list(self._bg_futures.items()) if f.done() and k != bid]:
            self._bg_futures.pop(k, None)
        return bid

    def g_waitkey(self, args):
        if self.gwin is None:
            raise MiniError("gwaitkey 需要先调用 gwin(宽, 高) 创建图形窗口")
        timeout = None
        if args:
            timeout = self._g_num(args[0], "gwaitkey", "超时毫秒")
        self._wait_key = None
        def on_key(e):
            self._wait_key = self._key_name(e)
        bid1 = self.gwin.bind("<KeyPress>", on_key)
        bid2 = None
        if self.gcanvas is not None:
            bid2 = self.gcanvas.bind("<KeyPress>", on_key)
        try:
            self.gwin.lift()
            self.gwin.focus_force()
            start = time.time()
            last_focus = 0
            while self._wait_key is None:
                self.gwin.update()
                now = time.time()
                if now - last_focus > 0.5:
                    try: self.gwin.focus_force()
                    except Exception: pass
                    last_focus = now
                time.sleep(0.01)
                if timeout is not None and (time.time() - start) * 1000 >= timeout:
                    return ""
        finally:
            try: self.gwin.unbind("<KeyPress>", bid1)
            except Exception: pass
            if bid2 is not None and self.gcanvas is not None:
                try: self.gcanvas.unbind("<KeyPress>", bid2)
                except Exception: pass
        return self._wait_key

    def g_waitclick(self, args):
        c = self.g_canvas()
        timeout = None
        if args:
            timeout = self._g_num(args[0], "gwaitclick", "超时毫秒")
        self._wait_click = None
        def on_click(e):
            self._wait_click = [float(e.x), float(e.y)]
        bid = c.bind("<Button-1>", on_click)
        try:
            self.gwin.lift()
            start = time.time()
            while self._wait_click is None:
                self.gwin.update()
                time.sleep(0.01)
                if timeout is not None and (time.time() - start) * 1000 >= timeout:
                    return []
        finally:
            try: c.unbind("<Button-1>", bid)
            except Exception: pass
        return self._wait_click

    def _need_fn(self, args, fname):
        if not args:
            raise MiniError(fname + " 需要一个函数参数")
        fn = args[0]
        if not isinstance(fn, (Fn, Native)):
            raise MiniError(fname + " 的参数必须是函数，得到：" + fmt(fn))
        return fn

    def g_keydown(self, args):
        fn = self._need_fn(args, "gkeydown")
        if self.gwin is None:
            raise MiniError("gkeydown 需要先调用 gwin(宽, 高) 创建图形窗口")
        def handler(e):
            try:
                self.call(fn, [self._key_name(e)], 0)
            except Exception as ex:
                self._cb_errors.append(str(ex))
        self.gwin.bind("<KeyPress>", handler)
        self.gwin.focus_force()
        return None

    def g_click(self, args):
        fn = self._need_fn(args, "gclick")
        c = self.g_canvas()
        def handler(e):
            try:
                self.call(fn, [float(e.x), float(e.y)], 0)
            except Exception as ex:
                self._cb_errors.append(str(ex))
        c.bind("<Button-1>", handler)
        return None

    def _f_path(self, v, fname):
        if not isinstance(v, str):
            raise MiniError(fname + " 的路径必须是字符串，得到：" + fmt(v))
        return v

    def f_readfile(self, args):
        if len(args) < 1:
            raise MiniError("readfile 需要 1 个参数：文件路径")
        p = self._f_path(args[0], "readfile")
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise MiniError("readfile 失败：文件不存在 " + p)
        except Exception as e:
            raise MiniError("readfile 失败：" + str(e))

    def _write_common(self, args, fname, mode):
        if len(args) < 2:
            raise MiniError(fname + " 需要 2 个参数：路径, 内容")
        p = self._f_path(args[0], fname)
        content = fmt(args[1])
        try:
            d = os.path.dirname(os.path.abspath(p))
            if d and not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)
            return None
        except Exception as e:
            raise MiniError(fname + " 失败：" + str(e))

    def f_writefile(self, args):
        return self._write_common(args, "writefile", "w")

    def f_appendfile(self, args):
        return self._write_common(args, "appendfile", "a")

    def f_exists(self, args):
        if len(args) < 1:
            raise MiniError("exists 需要 1 个参数：路径")
        p = self._f_path(args[0], "exists")
        return bool(os.path.exists(p))

    def f_files(self, args):
        p = self._f_path(args[0], "files") if args else "."
        try:
            return sorted(os.listdir(p))
        except FileNotFoundError:
            raise MiniError("files 失败：目录不存在 " + p)
        except Exception as e:
            raise MiniError("files 失败：" + str(e))

    def f_openfile(self, args):
        if len(args) < 1:
            raise MiniError("openfile 需要 1 个参数：文件路径")
        p = self._f_path(args[0], "openfile")
        if not os.path.exists(p):
            raise MiniError("openfile 失败：文件不存在 " + p)
        try:
            os.startfile(p)
        except AttributeError:
            raise MiniError("openfile 目前只支持 Windows 系统")
        except Exception as e:
            raise MiniError("openfile 失败：" + str(e))
        return None

    def f_openurl(self, args):
        if len(args) < 1:
            raise MiniError("openurl 需要 1 个参数：网址")
        url = self._f_path(args[0], "openurl")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise MiniError("openurl 的网址必须以 http:// 或 https:// 开头")
        try:
            webbrowser.open(url)
        except Exception as e:
            raise MiniError("openurl 失败：" + str(e))
        return None

    def f_runapp(self, args):
        if len(args) < 1:
            raise MiniError("runapp 需要 1 个参数：程序名或命令")
        cmd = self._f_path(args[0], "runapp")
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            raise MiniError("runapp 失败：" + str(e))
        return None

    # ===== 网络（阻塞版，主线程用） =====
    def _http_fetch(self, url, timeout=30, headers=None, max_bytes=None):
        """同步 GET，返回 bytes。内部用，http_get / http_download 共用。"""
        if not isinstance(url, str):
            raise MiniError("网址必须是字符串，得到：" + fmt(url))
        if not (url.startswith("http://") or url.startswith("https://")):
            raise MiniError("网址必须以 http:// 或 https:// 开头")
        req = urllib.request.Request(url, headers=headers or {
            "User-Agent": "HX-Lang/2.0"
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read(max_bytes) if max_bytes else resp.read()
                return data
        except urllib.error.HTTPError as e:
            raise MiniError("HTTP %d：%s" % (e.code, e.reason))
        except urllib.error.URLError as e:
            raise MiniError("网络错误：" + str(e.reason))
        except Exception as e:
            raise MiniError("请求失败：" + str(e))

    def h_http_get(self, args):
        if len(args) < 1:
            raise MiniError("http_get 需要 1 个参数：网址")
        url = args[0]
        timeout = 30
        if len(args) > 1 and self._is_num(args[1]):
            timeout = int(args[1]) / 1000.0
        data = self._http_fetch(url, timeout=timeout, max_bytes=10 * 1024 * 1024)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    def h_http_download(self, args):
        if len(args) < 2:
            raise MiniError("http_download 需要 2 个参数：网址, 保存路径")
        url = args[0]
        path = self._f_path(args[1], "http_download")
        timeout = 60
        if len(args) > 2 and self._is_num(args[2]):
            timeout = int(args[2]) / 1000.0
        d = os.path.dirname(os.path.abspath(path))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        data = self._http_fetch(url, timeout=timeout)
        try:
            with open(path, "wb") as f:
                f.write(data)
        except Exception as e:
            raise MiniError("http_download 写文件失败：" + str(e))
        return float(len(data))

    # ===== 后台任务 =====
    def h_bg_run(self, args):
        """在后台线程执行一个内置 IO 函数，完成后在主线程调用回调。
        用法：bg_run(函数, 参数..., [回调])"""
        if len(args) < 1:
            raise MiniError("bg_run 需要至少 1 个参数：函数, [参数...], [回调]")
        fn = args[0]
        if not isinstance(fn, Native):
            raise MiniError("bg_run 的函数必须是内置 IO 函数（http_get / http_download / readfile / md5 / sha256 / unzip 等）")
        rest = list(args[1:])
        callback = None
        if rest and isinstance(rest[-1], (Fn, Native)):
            callback = rest.pop()
        call_args = list(rest)

        def worker():
            return fn.fn(call_args)

        self._submit_bg(worker, callback)
        return None

    # ===== 解压 / 哈希（Python 原型；接口与未来 C dll 一致） =====
    def _h_path(self, v, fname):
        if not isinstance(v, str):
            raise MiniError(fname + " 的路径必须是字符串，得到：" + fmt(v))
        return v

    def h_md5(self, args):
        if len(args) < 1:
            raise MiniError("md5 需要 1 个参数：文件路径")
        p = self._h_path(args[0], "md5")
        h = hashlib.md5()
        try:
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        except FileNotFoundError:
            raise MiniError("md5 失败：文件不存在 " + p)
        except Exception as e:
            raise MiniError("md5 失败：" + str(e))
        return h.hexdigest()

    def h_sha256(self, args):
        if len(args) < 1:
            raise MiniError("sha256 需要 1 个参数：文件路径")
        p = self._h_path(args[0], "sha256")
        h = hashlib.sha256()
        try:
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        except FileNotFoundError:
            raise MiniError("sha256 失败：文件不存在 " + p)
        except Exception as e:
            raise MiniError("sha256 失败：" + str(e))
        return h.hexdigest()

    def h_unzip(self, args):
        if len(args) < 2:
            raise MiniError("unzip 需要 2 个参数：压缩包路径, 目标目录")
        src = self._h_path(args[0], "unzip")
        dst = self._h_path(args[1], "unzip")
        if not os.path.isfile(src):
            raise MiniError("unzip 失败：压缩包不存在 " + src)
        os.makedirs(dst, exist_ok=True)
        try:
            with zipfile.ZipFile(src, "r") as zf:
                # 防 Zip Slip：校验每个成员解压后仍在目标目录内
                base = os.path.abspath(dst)
                for name in zf.namelist():
                    target = os.path.abspath(os.path.join(base, name))
                    if not (target == base or target.startswith(base + os.sep)):
                        raise MiniError("unzip 拒绝非法路径：" + name)
                zf.extractall(dst)
                return float(len(zf.namelist()))
        except MiniError:
            raise
        except zipfile.BadZipFile:
            raise MiniError("unzip 失败：不是有效的 zip 文件")
        except Exception as e:
            raise MiniError("unzip 失败：" + str(e))

    def h_zipinfo(self, args):
        if len(args) < 1:
            raise MiniError("zipinfo 需要 1 个参数：压缩包路径")
        src = self._h_path(args[0], "zipinfo")
        if not os.path.isfile(src):
            raise MiniError("zipinfo 失败：压缩包不存在 " + src)
        try:
            with zipfile.ZipFile(src, "r") as zf:
                out = []
                for info in zf.infolist():
                    out.append([info.filename, float(info.file_size)])
                return out
        except zipfile.BadZipFile:
            raise MiniError("zipinfo 失败：不是有效的 zip 文件")
        except Exception as e:
            raise MiniError("zipinfo 失败：" + str(e))

    # ===== UI 运行时（PyQt5） =====
    def _ui_need_win(self, fname):
        if self.ui_win_obj is None:
            raise MiniError(fname + " 需要先调用 uiwin(宽, 高, 标题)")

    def _ui_args_num(self, args, idx, fname, pname):
        if idx >= len(args):
            raise MiniError(fname + " 缺少参数 " + pname)
        return self._g_num(args[idx], fname, pname)

    def _ui_id(self, args, fname):
        if not args or not isinstance(args[0], str):
            raise MiniError(fname + " 的第一个参数必须是组件 id（字符串）")
        return args[0]

    def _ui_place(self, args, fname):
        x = self._ui_args_num(args, 1, fname, "x")
        y = self._ui_args_num(args, 2, fname, "y")
        w = self._ui_args_num(args, 3, fname, "宽")
        h = self._ui_args_num(args, 4, fname, "高")
        return int(x), int(y), int(w), int(h)

    def ui_win(self, args):
        from PyQt5.QtWidgets import QWidget
        if len(args) < 3:
            raise MiniError("uiwin 需要 3 个参数：宽, 高, 标题")
        w = int(self._ui_args_num(args, 0, "uiwin", "宽"))
        h = int(self._ui_args_num(args, 1, "uiwin", "高"))
        title = str(args[2])
        if w <= 0 or h <= 0:
            raise MiniError("uiwin 的宽和高必须大于 0")
        if self.ui_win_obj is not None:
            try: self.ui_win_obj.close()
            except Exception: pass
        self.ui_widgets = {}
        self.ui_handlers = {}
        try:
            _qt_app()
            self.ui_win_obj = QWidget()
            self.ui_win_obj.setWindowTitle(title)
            self.ui_win_obj.resize(w, h)
            self.ui_win_obj.setStyleSheet(_UI_QSS)
        except Exception as e:
            raise MiniError("uiwin 创建窗口失败：" + str(e))
        return None

    def ui_btn(self, args):
        from PyQt5.QtWidgets import QPushButton
        self._ui_need_win("uibtn")
        if len(args) < 6:
            raise MiniError("uibtn 需要 6 个参数：(id, x, y, 宽, 高, 文字)")
        wid = self._ui_id(args, "uibtn")
        x, y, w, h = self._ui_place(args, "uibtn")
        text = str(args[5])
        try:
            b = QPushButton(text, self.ui_win_obj)
            b.setGeometry(x, y, w, h)
            self.ui_widgets[wid] = b
        except Exception as e:
            raise MiniError("uibtn 创建失败：" + str(e))
        return None

    def ui_label(self, args):
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt
        self._ui_need_win("uilabel")
        if len(args) < 6:
            raise MiniError("uilabel 需要 6 个参数：(id, x, y, 宽, 高, 文字)")
        wid = self._ui_id(args, "uilabel")
        x, y, w, h = self._ui_place(args, "uilabel")
        text = str(args[5])
        try:
            lb = QLabel(text, self.ui_win_obj)
            lb.setGeometry(x, y, w, h)
            lb.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.ui_widgets[wid] = lb
        except Exception as e:
            raise MiniError("uilabel 创建失败：" + str(e))
        return None

    def ui_heading(self, args):
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt
        self._ui_need_win("uiheading")
        if len(args) < 6:
            raise MiniError("uiheading 需要 6 个参数：(id, x, y, 宽, 高, 文字)")
        wid = self._ui_id(args, "uiheading")
        x, y, w, h = self._ui_place(args, "uiheading")
        text = str(args[5])
        try:
            lb = QLabel(text, self.ui_win_obj)
            lb.setGeometry(x, y, w, h)
            lb.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            lb.setStyleSheet("font-size:15pt;font-weight:bold;color:#1c1917;background:transparent;")
            self.ui_widgets[wid] = lb
        except Exception as e:
            raise MiniError("uiheading 创建失败：" + str(e))
        return None

    def ui_input(self, args):
        from PyQt5.QtWidgets import QLineEdit
        self._ui_need_win("uiinput")
        if len(args) < 5:
            raise MiniError("uiinput 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uiinput")
        x, y, w, h = self._ui_place(args, "uiinput")
        try:
            e = QLineEdit(self.ui_win_obj)
            e.setGeometry(x, y, w, h)
            self.ui_widgets[wid] = e
        except Exception as e2:
            raise MiniError("uiinput 创建失败：" + str(e2))
        return None

    def ui_text(self, args):
        from PyQt5.QtWidgets import QTextEdit
        self._ui_need_win("uitext")
        if len(args) < 5:
            raise MiniError("uitext 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uitext")
        x, y, w, h = self._ui_place(args, "uitext")
        try:
            t = QTextEdit(self.ui_win_obj)
            t.setGeometry(x, y, w, h)
            self.ui_widgets[wid] = t
        except Exception as e2:
            raise MiniError("uitext 创建失败：" + str(e2))
        return None

    def ui_check(self, args):
        from PyQt5.QtWidgets import QCheckBox
        self._ui_need_win("uicheck")
        if len(args) < 4:
            raise MiniError("uicheck 需要 4 个参数：(id, x, y, 文字)")
        wid = self._ui_id(args, "uicheck")
        x = self._ui_args_num(args, 1, "uicheck", "x")
        y = self._ui_args_num(args, 2, "uicheck", "y")
        text = str(args[3])
        try:
            cb = QCheckBox(text, self.ui_win_obj)
            cb.move(int(x), int(y))
            cb.adjustSize()
            self.ui_widgets[wid] = cb
        except Exception as e2:
            raise MiniError("uicheck 创建失败：" + str(e2))
        return None

    def ui_radio(self, args):
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QWidget
        self._ui_need_win("uiradio")
        if len(args) < 6:
            raise MiniError("uiradio 需要 6 个参数：(id, x, y, 宽, 高, 选项数组)")
        wid = self._ui_id(args, "uiradio")
        x, y, w, h = self._ui_place(args, "uiradio")
        items = args[5]
        if not isinstance(items, list):
            raise MiniError("uiradio 的第 6 个参数必须是数组")
        try:
            holder = QWidget(self.ui_win_obj)
            holder.setGeometry(x, y, w, h)
            holder.setStyleSheet("background:transparent;")
            group = QButtonGroup(holder)
            btns = []
            for i, it in enumerate(items):
                rb = QRadioButton(fmt(it), holder)
                rb.move(0, i * 22)
                rb.adjustSize()
                group.addButton(rb, i)
                btns.append(rb)
            if btns:
                btns[0].setChecked(True)
            holder._hx_group = group
            holder._hx_buttons = btns
            self.ui_widgets[wid] = holder
        except Exception as e:
            raise MiniError("uiradio 创建失败：" + str(e))
        return None

    def ui_combo(self, args):
        from PyQt5.QtWidgets import QComboBox
        self._ui_need_win("uicombo")
        if len(args) < 6:
            raise MiniError("uicombo 需要 6 个参数：(id, x, y, 宽, 高, 选项数组)")
        wid = self._ui_id(args, "uicombo")
        x, y, w, h = self._ui_place(args, "uicombo")
        items = args[5]
        if not isinstance(items, list):
            raise MiniError("uicombo 的第 6 个参数必须是数组")
        try:
            cb = QComboBox(self.ui_win_obj)
            cb.setGeometry(x, y, w, h)
            for it in items:
                cb.addItem(fmt(it))
            self.ui_widgets[wid] = cb
        except Exception as e:
            raise MiniError("uicombo 创建失败：" + str(e))
        return None

    def ui_list(self, args):
        from PyQt5.QtWidgets import QListWidget
        self._ui_need_win("uilist")
        if len(args) < 6:
            raise MiniError("uilist 需要 6 个参数：(id, x, y, 宽, 高, 选项数组)")
        wid = self._ui_id(args, "uilist")
        x, y, w, h = self._ui_place(args, "uilist")
        items = args[5]
        if not isinstance(items, list):
            raise MiniError("uilist 的第 6 个参数必须是数组")
        try:
            lb = QListWidget(self.ui_win_obj)
            lb.setGeometry(x, y, w, h)
            for it in items:
                lb.addItem(fmt(it))
            self.ui_widgets[wid] = lb
        except Exception as e2:
            raise MiniError("uilist 创建失败：" + str(e2))
        return None

    def ui_range(self, args):
        from PyQt5.QtWidgets import QSlider
        from PyQt5.QtCore import Qt
        self._ui_need_win("uirange")
        if len(args) < 5:
            raise MiniError("uirange 需要 5 个参数：(id, x, y, 宽, 最大值)")
        wid = self._ui_id(args, "uirange")
        x = self._ui_args_num(args, 1, "uirange", "x")
        y = self._ui_args_num(args, 2, "uirange", "y")
        w = self._ui_args_num(args, 3, "uirange", "宽")
        mx = self._ui_args_num(args, 4, "uirange", "最大值")
        try:
            sc = QSlider(Qt.Horizontal, self.ui_win_obj)
            sc.setGeometry(int(x), int(y), int(w), 24)
            sc.setRange(0, int(mx))
            self.ui_widgets[wid] = sc
        except Exception as e2:
            raise MiniError("uirange 创建失败：" + str(e2))
        return None

    def ui_progress(self, args):
        from PyQt5.QtWidgets import QProgressBar
        self._ui_need_win("uiprogress")
        if len(args) < 5:
            raise MiniError("uiprogress 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uiprogress")
        x, y, w, h = self._ui_place(args, "uiprogress")
        try:
            pb = QProgressBar(self.ui_win_obj)
            pb.setGeometry(x, y, w, h)
            pb.setRange(0, 100)
            pb.setValue(0)
            pb.setTextVisible(False)
            self.ui_widgets[wid] = pb
        except Exception as e2:
            raise MiniError("uiprogress 创建失败：" + str(e2))
        return None

    def ui_image(self, args):
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt
        self._ui_need_win("uiimage")
        if len(args) < 5:
            raise MiniError("uiimage 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uiimage")
        x, y, w, h = self._ui_place(args, "uiimage")
        try:
            lb = QLabel(self.ui_win_obj)
            lb.setGeometry(x, y, w, h)
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet("background:#ffffff;border:1px solid #e7e5e4;border-radius:6px;")
            lb._hx_w = w
            lb._hx_h = h
            lb._hx_path = ""
            lb._hx_pixmap = None
            self.ui_widgets[wid] = lb
        except Exception as e:
            raise MiniError("uiimage 创建失败：" + str(e))
        return None

    def ui_table(self, args):
        from PyQt5.QtWidgets import QTableWidget, QHeaderView
        self._ui_need_win("uitable")
        if len(args) < 6:
            raise MiniError("uitable 需要 6 个参数：(id, x, y, 宽, 高, 列名数组)")
        wid = self._ui_id(args, "uitable")
        x, y, w, h = self._ui_place(args, "uitable")
        cols = args[5]
        if not isinstance(cols, list):
            raise MiniError("uitable 的第 6 个参数必须是数组")
        try:
            tv = QTableWidget(self.ui_win_obj)
            tv.setGeometry(x, y, w, h)
            tv.setColumnCount(len(cols))
            tv.setHorizontalHeaderLabels([fmt(c) for c in cols])
            tv.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tv.verticalHeader().setVisible(False)
            tv.setRowCount(0)
            self.ui_widgets[wid] = tv
        except Exception as e:
            raise MiniError("uitable 创建失败：" + str(e))
        return None

    def ui_panel(self, args):
        from PyQt5.QtWidgets import QFrame
        self._ui_need_win("uipanel")
        if len(args) < 5:
            raise MiniError("uipanel 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uipanel")
        x, y, w, h = self._ui_place(args, "uipanel")
        try:
            f = QFrame(self.ui_win_obj)
            f.setGeometry(x, y, w, h)
            f.setStyleSheet("QFrame{background:#ffffff;border:1px solid #e7e5e4;border-radius:6px;}")
            self.ui_widgets[wid] = f
        except Exception as e:
            raise MiniError("uipanel 创建失败：" + str(e))
        return None

    def ui_separator(self, args):
        from PyQt5.QtWidgets import QFrame
        self._ui_need_win("uiseparator")
        if len(args) < 4:
            raise MiniError("uiseparator 需要 4 个参数：(id, x, y, 宽)")
        wid = self._ui_id(args, "uiseparator")
        x = self._ui_args_num(args, 1, "uiseparator", "x")
        y = self._ui_args_num(args, 2, "uiseparator", "y")
        w = self._ui_args_num(args, 3, "uiseparator", "宽")
        try:
            line = QFrame(self.ui_win_obj)
            line.setGeometry(int(x), int(y), int(w), 1)
            line.setStyleSheet("background:#e7e5e4;border:none;")
            self.ui_widgets[wid] = line
        except Exception as e:
            raise MiniError("uiseparator 创建失败：" + str(e))
        return None

    def ui_tabs(self, args):
        from PyQt5.QtWidgets import QTabWidget, QWidget
        self._ui_need_win("uitabs")
        if len(args) < 6:
            raise MiniError("uitabs 需要 6 个参数：(id, x, y, 宽, 高, 标签名数组)")
        wid = self._ui_id(args, "uitabs")
        x, y, w, h = self._ui_place(args, "uitabs")
        items = args[5]
        if not isinstance(items, list):
            raise MiniError("uitabs 的第 6 个参数必须是数组")
        try:
            nb = QTabWidget(self.ui_win_obj)
            nb.setGeometry(x, y, w, h)
            for it in items:
                page = QWidget()
                nb.addTab(page, fmt(it))
            self.ui_widgets[wid] = nb
        except Exception as e:
            raise MiniError("uitabs 创建失败：" + str(e))
        return None

    def ui_on(self, args):
        from PyQt5.QtWidgets import (QPushButton, QCheckBox, QComboBox, QListWidget,
                                     QSlider, QLineEdit, QTextEdit, QTabWidget,
                                     QWidget)
        if len(args) < 3:
            raise MiniError("uion 需要 3 个参数：(组件id, 事件名, 函数)")
        wid = self._ui_id(args, "uion")
        event = str(args[1])
        fn = args[2]
        if not isinstance(fn, (Fn, Native)):
            raise MiniError("uion 的第 3 个参数必须是函数")
        if wid not in self.ui_widgets:
            raise MiniError("uion 找不到组件 " + wid)
        w = self.ui_widgets[wid]

        def handler(*a):
            try:
                self.call(fn, [], 0)
            except Exception as ex:
                self._cb_errors.append(str(ex))

        try:
            if isinstance(w, QPushButton):
                if event != "click":
                    raise MiniError("按钮只支持 click 事件")
                w.clicked.connect(handler)
            elif isinstance(w, QCheckBox):
                if event not in ("click", "change"):
                    raise MiniError("勾选框支持 click / change 事件")
                w.stateChanged.connect(handler)
            elif isinstance(w, QLineEdit):
                if event not in ("change", "select"):
                    raise MiniError("输入框支持 change / select 事件")
                w.textChanged.connect(handler)
            elif isinstance(w, QTextEdit):
                if event != "change":
                    raise MiniError("多行文本只支持 change 事件")
                w.textChanged.connect(handler)
            elif isinstance(w, QComboBox):
                if event not in ("change", "select"):
                    raise MiniError("下拉框支持 change / select 事件")
                w.currentIndexChanged.connect(handler)
            elif isinstance(w, QListWidget):
                if event not in ("change", "select"):
                    raise MiniError("列表支持 change / select 事件")
                w.currentRowChanged.connect(handler)
            elif isinstance(w, QSlider):
                if event != "change":
                    raise MiniError("滑块只支持 change 事件")
                w.valueChanged.connect(handler)
            elif isinstance(w, QTabWidget):
                if event != "select":
                    raise MiniError("标签页只支持 select 事件")
                w.currentChanged.connect(handler)
            elif isinstance(w, QWidget) and hasattr(w, "_hx_group"):
                if event not in ("click", "change"):
                    raise MiniError("单选组支持 click / change 事件")
                w._hx_group.buttonClicked.connect(handler)
            else:
                raise MiniError("组件 " + wid + " 不支持绑定事件")
        except MiniError:
            raise
        except Exception as ex:
            raise MiniError("uion 绑定失败：" + str(ex))
        return None

    def ui_get(self, args):
        from PyQt5.QtWidgets import (QPushButton, QCheckBox, QComboBox, QListWidget,
                                     QSlider, QLineEdit, QTextEdit, QTabWidget,
                                     QProgressBar, QLabel, QTableWidget, QWidget)
        wid = self._ui_id(args, "uiget")
        if wid not in self.ui_widgets:
            raise MiniError("uiget 找不到组件 " + wid)
        w = self.ui_widgets[wid]
        try:
            if isinstance(w, QLineEdit):
                return w.text()
            if isinstance(w, QTextEdit):
                return w.toPlainText()
            if isinstance(w, QCheckBox):
                return bool(w.isChecked())
            if isinstance(w, QComboBox):
                return w.currentText()
            if isinstance(w, QListWidget):
                it = w.currentItem()
                return it.text() if it else ""
            if isinstance(w, QSlider):
                return float(w.value())
            if isinstance(w, QProgressBar):
                return float(w.value())
            if isinstance(w, QTabWidget):
                return w.tabText(w.currentIndex()) if w.count() else ""
            if isinstance(w, QTableWidget):
                row = w.currentRow()
                if row < 0:
                    return []
                return [(w.item(row, c).text() if w.item(row, c) else "")
                        for c in range(w.columnCount())]
            if isinstance(w, QWidget) and hasattr(w, "_hx_group"):
                cid = w._hx_group.checkedId()
                if 0 <= cid < len(w._hx_buttons):
                    return w._hx_buttons[cid].text()
                return ""
            if isinstance(w, QWidget) and hasattr(w, "_hx_path"):
                return getattr(w, "_hx_path", "")
            if isinstance(w, QLabel):
                return w.text()
            if isinstance(w, QPushButton):
                return w.text()
        except Exception as ex:
            raise MiniError("uiget 失败：" + str(ex))
        return ""

    def ui_set(self, args):
        from PyQt5.QtWidgets import (QPushButton, QCheckBox, QComboBox, QListWidget,
                                     QSlider, QLineEdit, QTextEdit, QTabWidget,
                                     QProgressBar, QLabel, QTableWidget, QWidget,
                                     QTableWidgetItem)
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        if len(args) < 2:
            raise MiniError("uiset 需要 2 个参数：(组件id, 值)")
        wid = self._ui_id(args, "uiset")
        if wid not in self.ui_widgets:
            raise MiniError("uiset 找不到组件 " + wid)
        w = self.ui_widgets[wid]
        val = args[1]
        try:
            if isinstance(w, QLineEdit):
                w.setText(fmt(val))
            elif isinstance(w, QTextEdit):
                w.setPlainText(fmt(val))
            elif isinstance(w, QCheckBox):
                w.setChecked(truth(val))
            elif isinstance(w, QComboBox):
                idx = w.findText(fmt(val))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif isinstance(w, QListWidget):
                w.clear()
                if isinstance(val, list):
                    for it in val:
                        w.addItem(fmt(it))
            elif isinstance(w, QSlider):
                w.setValue(int(val) if self._is_num(val) else 0)
            elif isinstance(w, QProgressBar):
                pct = int(val) if self._is_num(val) else 0
                w.setValue(max(0, min(100, pct)))
            elif isinstance(w, QTabWidget):
                for i in range(w.count()):
                    if w.tabText(i) == fmt(val):
                        w.setCurrentIndex(i)
                        break
            elif isinstance(w, QTableWidget):
                w.setRowCount(0)
                if isinstance(val, list):
                    for r in val:
                        if isinstance(r, list):
                            row = w.rowCount()
                            w.insertRow(row)
                            for c, cell in enumerate(r[:w.columnCount()]):
                                w.setItem(row, c, QTableWidgetItem(fmt(cell)))
            elif isinstance(w, QWidget) and hasattr(w, "_hx_group"):
                for btn in w._hx_buttons:
                    if btn.text() == fmt(val):
                        btn.setChecked(True)
                        break
            elif isinstance(w, QWidget) and hasattr(w, "_hx_path"):
                path = fmt(val)
                w._hx_path = path
                try:
                    pix = QPixmap(path)
                    if pix.isNull():
                        w.setText("图片载入失败")
                    else:
                        scaled = pix.scaled(w._hx_w, w._hx_h,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        w.setPixmap(scaled)
                        w._hx_pixmap = scaled
                except Exception:
                    w.setText("图片载入失败")
            elif isinstance(w, (QLabel, QPushButton)):
                w.setText(fmt(val))
        except Exception as ex:
            raise MiniError("uiset 失败：" + str(ex))
        return None

    def ui_run(self, args):
        self._ui_need_win("uirun")
        app = _qt_app()
        self.ui_running = True
        err = None
        try:
            self.ui_win_obj.show()
            while True:
                app.processEvents()
                self.poll_bg_tasks()
                time.sleep(0.01)
                self._check_cb_errors()
                if not self.ui_win_obj.isVisible():
                    break
        except MiniError as e:
            err = e
        except Exception as e:
            err = MiniError("uirun 出错：" + str(e))
        finally:
            self.ui_running = False
        if err is not None:
            raise err
        return None

    def close_gwin(self):
        if self.gwin is not None:
            try: self.gwin.destroy()
            except Exception: pass
            self.gwin=None; self.gcanvas=None

    def mark(self,line):
        if len(self.trace)<3000:
            self.trace.append((line,{k:fmt(v) for k,v in self.globals.vars.items()},len(self.outbuf)))

    def run(self,prog):
        try:
            self.ex(prog)
        except Return:
            pass

    def ex(self,n):
        try:
            self._ex(n)
        except (Return,MiniError,BreakSig,ContinueSig):
            raise
        except ZeroDivisionError:
            raise MiniError("第 %d 行：除数为 0" % n[-1])
        except NameError as e:
            raise MiniError("第 %d 行：%s" % (n[-1],e))
        except Exception as e:
            raise MiniError("第 %d 行：%s" % (n[-1],e))

    def _ex(self,n):
        self.steps+=1
        if self.steps>self.maxsteps:
            raise MiniError("执行步数超限（疑似死循环）")
        self.mark(n[-1])
        k=n[0]
        if k=="block":
            for s in n[1]: self.ex(s)
        elif k=="func":
            self.env.define(n[1],Fn(n[2],n[3],self.env,n[1]))
        elif k=="return":
            raise Return(self.ev(n[1]) if n[1] is not None else None)
        elif k=="expr":
            self.ev(n[1])
        elif k=="call":
            self.ev(n)
        elif k=="try":
            _,body,nm,handler,ln=n
            try:
                self.ex(body)
            except MiniError as e:
                ne=Env(self.env); ne.define(nm,str(e))
                old=self.env; self.env=ne
                try: self.ex(handler)
                finally: self.env=old
        elif k=="if":
            if truth(self.ev(n[1])): self.ex(n[2])
            elif n[3] is not None: self.ex(n[3])
        elif k=="while":
            while truth(self.ev(n[1])):
                try: self.ex(n[2])
                except BreakSig: break
                except ContinueSig: continue
        elif k=="scanf":
            self.do_scanf(n[1], n[2], n[-1])
        elif k=="forc":
            _,init,cond,step,body,ln=n
            if init is not None: self.ev(init)
            while cond is None or truth(self.ev(cond)):
                try: self.ex(body)
                except BreakSig: break
                except ContinueSig: pass
                if step is not None: self.ev(step)
        elif k=="break":
            raise BreakSig()
        elif k=="continue":
            raise ContinueSig()
        elif k=="del":
            self.deleting(n[1])
        else:
            raise MiniError("无法执行 %s" % k)

    def _is_num(self, v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _vdesc(self, v):
        t = typename(v)
        s = fmt(v)
        if len(s) > 30:
            s = s[:27] + "..."
        if t == "字符串":
            s = '"' + s + '"'
        return t + " " + s

    def _need_nums(self, l, r, op, ln):
        if not self._is_num(l) or not self._is_num(r):
            raise MiniError("第 %d 行：%s 需要两个数字，得到 %s 和 %s"
                            % (ln, op, self._vdesc(l), self._vdesc(r)))

    def _need_cmp(self, l, r, op, ln):
        if self._is_num(l) and self._is_num(r):
            return
        if isinstance(l, str) and isinstance(r, str):
            return
        raise MiniError("第 %d 行：%s 两边类型不匹配，得到 %s 和 %s"
                        % (ln, op, self._vdesc(l), self._vdesc(r)))

    def ev(self,n):
        k=n[0]
        if k in ("num","str","bool","null"): return n[1]
        if k=="cat": return "".join(fmt(self.ev(p)) for p in n[1])
        if k=="id": return self.env.get(n[1])
        if k=="list": return [self.ev(x) for x in n[1]]
        if k=="dict": return dict((kk,self.ev(v)) for kk,v in n[1])
        if k=="un":
            v=self.ev(n[2])
            if n[1]=="-":
                if not self._is_num(v):
                    raise MiniError("第 %d 行：负号只能用于数字，得到 %s"
                                    % (n[-1], self._vdesc(v)))
                return -v
            return not truth(v)
        if k=="bin":
            op=n[1]
            if op=="and":
                l=self.ev(n[2])
                return self.ev(n[3]) if truth(l) else l
            if op=="or":
                l=self.ev(n[2])
                return l if truth(l) else self.ev(n[3])
            l=self.ev(n[2]); r=self.ev(n[3])
            ln=n[-1]
            if op=="==": return l==r
            if op=="!=": return l!=r
            if op=="+":
                if isinstance(l,str) or isinstance(r,str): return fmt(l)+fmt(r)
                if isinstance(l,list) and isinstance(r,list):
                    raise MiniError("第 %d 行：数组不能用 + 拼接，请用 push 逐个添加" % ln)
                self._need_nums(l,r,"+",ln)
                return l+r
            if op=="-":
                self._need_nums(l,r,"-",ln)
                return l-r
            if op=="*":
                self._need_nums(l,r,"*",ln)
                return l*r
            if op=="/":
                self._need_nums(l,r,"/",ln)
                if r==0: raise MiniError("第 %d 行：除数为 0" % ln)
                return l/r
            if op=="%":
                self._need_nums(l,r,"%",ln)
                if r==0: raise MiniError("第 %d 行：取模的除数为 0" % ln)
                return l%r
            if op=="<":
                self._need_cmp(l,r,"<",ln); return l<r
            if op==">":
                self._need_cmp(l,r,">",ln); return l>r
            if op=="<=":
                self._need_cmp(l,r,"<=",ln); return l<=r
            if op==">=":
                self._need_cmp(l,r,">=",ln); return l>=r
            raise MiniError("第 %d 行：未知运算符 %s" % (ln, op))
        if k=="set":
            v=self.ev(n[2]); self.assign(n[1],v); return v
        if k=="call":
            f=self.ev(n[1]); args=[self.ev(a) for a in n[2]]
            return self.call(f,args,n[-1])
        if k=="idx":
            return self.index(self.ev(n[1]),self.ev(n[2]),n[-1])
        if k=="attr":
            c=self.ev(n[1])
            if isinstance(c,dict) and n[2] in c: return c[n[2]]
            raise MiniError("第 %d 行：没有属性 %s" % (n[-1],n[2]))
        raise MiniError("无法求值 %s" % k)

    def deleting(self,node):
        k=node[0]
        if k=="idx":
            c=self.ev(node[1]); i=self.ev(node[2])
            if isinstance(c,dict):
                if i in c: del c[i]; return
                raise MiniError("第 %d 行：字典没有键 %s" % (node[-1],fmt(i)))
            if isinstance(c,list):
                kk=int(i)
                if 0<=kk<len(c): del c[kk]; return
                raise MiniError("第 %d 行：下标越界" % node[-1])
            raise MiniError("第 %d 行：不能删除 %s 的元素" % (node[-1],fmt(c)))
        if k=="attr":
            c=self.ev(node[1])
            if isinstance(c,dict) and node[2] in c:
                del c[node[2]]; return
            raise MiniError("第 %d 行：字典没有键 %s" % (node[-1],node[2]))
        raise MiniError("第 %d 行：del 只支持 d[k] 或 d.k" % node[-1])

    def index(self,c,i,line):
        if isinstance(c,(list,str)):
            k=int(i)
            if k<0 or k>=len(c): raise MiniError("第 %d 行：下标越界 %d" % (line,k))
            return c[k]
        if isinstance(c,dict):
            if i in c: return c[i]
            raise MiniError("第 %d 行：字典没有键 %s" % (line,fmt(i)))
        raise MiniError("第 %d 行：不能下标访问 %s" % (line,fmt(c)))

    def assign(self,node,v):
        k=node[0]
        if k=="id":
            try: self.env.set(node[1],v)
            except NameError: self.env.define(node[1],v)
            return
        if k=="idx":
            c=self.ev(node[1]); i=self.ev(node[2])
            if isinstance(c,list):
                kk=int(i)
                if kk<0 or kk>=len(c): raise MiniError("第 %d 行：下标越界 %d" % (node[-1],kk))
                c[kk]=v; return
            if isinstance(c,dict): c[i]=v; return
            raise MiniError("第 %d 行：不能赋值下标" % node[-1])
        if k=="attr":
            c=self.ev(node[1])
            if isinstance(c,dict): c[node[2]]=v; return
            raise MiniError("第 %d 行：不能设置属性" % node[-1])
        raise MiniError("第 %d 行：非法赋值目标" % node[-1])

    def call(self,f,args,line):
        if isinstance(f,Native):
            try: return f.fn(args)
            except MiniError: raise
            except Exception as e: raise MiniError("第 %d 行：%s" % (line,e))
        if isinstance(f,Fn):
            env=Env(f.env)
            for i,p in enumerate(f.params):
                env.define(p,args[i] if i<len(args) else None)
            saved=self.env; self.env=env
            try:
                self.ex(f.body); return None
            except Return as r:
                return r.value
            finally:
                self.env=saved
        raise MiniError("第 %d 行：%s 不是函数" % (line,fmt(f)))


CHEATSHEET = {
"变量": [
  "x = 10;              直接赋值，自动判断类型（无需声明）",
  'x = "hi";            同样自动识别 字符串/数组/字典/布尔 等',
  "type(x)              查询类型：数字/字符串/布尔/数组/字典/函数/空",
  "true / false / null  布尔与空值字面量",
  "注意：let / dar 声明写法已移除，直接写 x = 1;",
],
"输出与输入": [
  'print("hi", 1);     输出，多参数用空格分隔',
  'print();             无参数输出一个空行',
  'input("提示")        读一行输入，返回字符串',
  'scanf("%d %d", a, b) 按格式读入多个值（变量需先声明）',
  '  格式：%d 整数  %f 数字  %s 字符串  %c 单字符',
  'help()               打印语法速查',
],
"函数": [
  "add(a, b) { return a + b; }     定义函数（C 风格）",
  "递归：fib(n){ if(n<2){return n;} return fib(n-1)+fib(n-2); }",
  "noop() { }                      无参函数",
],
"控制流": [
  "if (c) { ... } else { ... }",
  "else if (c) { ... }       多分支，串在 else 后面（没有 elif）",
  "while (c) { ... }",
  "for (i = 0; i < n; i += 1) { ... }   C 式三段循环，三段均可省略",
  "遍历数组：for (i = 0; i < len(a); i += 1) { print(a[i]); }",
  "遍历字典：ks = keys(d); for (i = 0; i < len(ks); i += 1) { print(ks[i]); }",
  "break;   continue;",
  "try { ... } catch (e) { ... }   捕获错误，e 为错误信息",
  "and / or / not        也可写 && / || / !",
],
"运算符": [
  "+ - * / %               算术",
  "== != < <= > >=         比较",
  "+= -= *= /= %=          复合赋值",
  "x = 1                   赋值（分号可省，未声明则自动创建）",
  "sqrt sin cos tan floor ceil round random   数学函数，PI 为圆周率",
],
"数组": [
  "a = [1, 2, 3];",
  "a[0]   a[0] = 9",
  "len(a)  push(a, 4)  min(a)  max(a)  abs(-3)",
  "range(5)  生成 [0, 1, 2, 3, 4]",
],
"字典": [
  'd = {name: "mini", ver: 3};',
  "d.name   d[\"name\"]   d.k = 1",
  "keys(d)  items(d)  has(d, \"k\")  set(d, \"k\", 1)",
  "del d.k   del d[\"k\"]",
],
"字符串": [
  '"hi" + 1                拼接，自动转字符串',
  'upper("ab")  lower("AB")  trim("  x  ")',
  'split("a-b", "-")  join("-", ["a","b"])',
  '"hi ${x}!"             字符串插值，${表达式} 求值后拼接',
  'str(3)   num("4.5")     转字符串 / 转数字',
],
"图形": [
  "gwin(600, 400);          创建图形窗口（宽, 高）",
  "gwin(600, 400, \"我的画板\");  创建带自定义标题的窗口",
  "gline(x1, y1, x2, y2, \"red\", 3);   画线（颜色、线宽可省）",
  "grect(x1, y1, x2, y2, \"black\", \"skyblue\");  矩形，最后一个参数为空串则空心",
  "gcircle(cx, cy, r, \"black\", \"yellow\");        圆",
  "gtext(x, y, \"你好\", \"blue\");         在指定位置写字",
  "gclear();                清空画面",
  "gsleep(500);             暂停 500 毫秒并刷新（做动画）",
],
"界面": [
  'uiwin(400, 300, "标题");     创建窗口',
  'uiheading("id", x, y, 宽, 高, "大标题");  标题',
  'uilabel("id", x, y, 宽, 高, "文字");      标签',
  'uibtn("id", x, y, 宽, 高, "按钮");        按钮',
  'uiinput("id", x, y, 宽, 高);              输入框',
  'uitext("id", x, y, 宽, 高);               多行文本',
  'uicheck("id", x, y, "选项");              勾选框',
  'uiradio("id", x, y, 宽, 高, ["A","B"]);   单选组',
  'uicombo("id", x, y, 宽, 高, ["A","B"]);   下拉框',
  'uilist("id", x, y, 宽, 高, ["a","b"]);    列表框',
  'uirange("id", x, y, 宽, 最大值);          滑块',
  'uiprogress("id", x, y, 宽, 高);           进度条',
  'uiimage("id", x, y, 宽, 高);              图片（uiset 传路径）',
  'uitable("id", x, y, 宽, 高, ["列1","列2"]);  表格',
  'uipanel("id", x, y, 宽, 高);              面板容器',
  'uiseparator("id", x, y, 宽);              分割线',
  'uitabs("id", x, y, 宽, 高, ["页1","页2"]);   标签页',
  'uion("id", "click", fn);               绑定事件（click/change/select）',
  'uiget("id")   uiset("id", 值)          读取 / 设置组件值',
  'uirun();                               启动界面事件循环',
],
"交互": [
  "k = gwaitkey();          等待按键，返回键名（如 \"a\", \"space\", \"enter\"）",
  "k = gwaitkey(3000);      最多等 3 秒，超时返回空字符串",
  "p = gwaitclick();        等待鼠标点击，返回 [x, y]",
  "gkeydown(on_key);        按键回调，函数收到键名参数",
  "gclick(on_click);        点击回调，函数收到 x, y 参数",
],
"网络与后台": [
  'http_get(url, 超时毫秒?)        同步 GET，返回文本',
  'http_download(url, 路径, 超时?) 同步下载，返回字节数',
  'bg_run(fn, 参数..., 回调)       后台执行内置 IO 函数，完成后主线程调回调',
  '  例：bg_run(http_get, "https://x", on_done)',
  '  注意：后台只跑内置 IO（http_get/readfile/md5 等），不能操作 UI',
  '  回调里可以安全操作 UI（在主线程执行）',
],
"压缩与哈希": [
  'md5(路径)              文件 MD5',
  'sha256(路径)           文件 SHA256',
  'zipinfo(路径)          返回 [[名称, 大小], ...]',
  'unzip(路径, 目标目录)  解压 zip，返回文件数（防 Zip Slip）',
],
"文件与系统": [
  'readfile("a.txt")        读取整个文件（UTF-8）',
  'writefile("a.txt", s)    写入文件（覆盖）',
  'appendfile("a.txt", s)   追加到文件末尾',
  'exists("a.txt")          判断文件/目录是否存在',
  'files(".")               列出目录内容，返回数组',
  'openfile("a.txt")        用系统默认程序打开文件',
  'openurl("https://...")   用默认浏览器打开网址',
  'runapp("notepad.exe")    启动外部程序',
],
"注释": ["# 这一行是注释"],
}

CHEAT_ORDER = ["变量","输出与输入","函数","控制流","运算符","数组","字典","字符串","界面","图形","交互","网络与后台","压缩与哈希","文件与系统","注释"]

def cheatsheet_text():
    lines = []
    for sec in CHEAT_ORDER:
        lines.append("【%s】" % sec)
        for item in CHEATSHEET[sec]:
            lines.append("  " + item)
        lines.append("")
    return "\n".join(lines)

if __name__=="__main__":
    args=sys.argv[1:]
    if not args:
        sys.stderr.write("用法: python hx.py <文件.hxg>\n")
        sys.exit(1)
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    try: sys.stdin.reconfigure(encoding="utf-8")
    except Exception: pass
    with open(args[0],encoding="utf-8") as f: src=f.read()
    it=Interp()
    try:
        it.run(Parser(tokenize(src)).program())
    except (SyntaxError,MiniError) as e:
        sys.stdout.write(it.text()+str(e)+"\n"); sys.exit(1)
    sys.stdout.write(it.text())
    if it.gwin is not None:
        try: it.gwin.mainloop()
        except Exception: pass
