# MiniLang v2 —— 解释器 + Tkinter 编码器
# 语法：x = 1;  f(a,b){...}  if/else if/else  while  for  return
#       print("hi", 1);  数组 [1,2]  字典 {a:1}  字符串 "x" 或 'x'  注释 #
import sys, re, os, math, json, threading, queue, time, subprocess, webbrowser
import urllib.request, urllib.error

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
        g.define("uiwin",Native(self.ui_win))
        g.define("uibtn",Native(self.ui_btn))
        g.define("uilabel",Native(self.ui_label))
        g.define("uiinput",Native(self.ui_input))
        g.define("uitext",Native(self.ui_text))
        g.define("uicheck",Native(self.ui_check))
        g.define("uilist",Native(self.ui_list))
        g.define("uirange",Native(self.ui_range))
        g.define("uiprogress",Native(self.ui_progress))
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
        try:
            if self.gwin is not None: self.gwin.update()
            time.sleep(max(0, ms)/1000.0)
            if self.gwin is not None: self.gwin.update()
        except Exception:
            time.sleep(max(0, ms)/1000.0)
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

    # ===== UI 运行时 =====
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

    def _ui_tk(self):
        import tkinter as tk
        return tk

    def ui_win(self, args):
        tk = self._ui_tk()
        if len(args) < 3:
            raise MiniError("uiwin 需要 3 个参数：宽, 高, 标题")
        w = int(self._ui_args_num(args, 0, "uiwin", "宽"))
        h = int(self._ui_args_num(args, 1, "uiwin", "高"))
        title = str(args[2])
        if w <= 0 or h <= 0:
            raise MiniError("uiwin 的宽和高必须大于 0")
        if self.ui_win_obj is not None:
            try: self.ui_win_obj.destroy()
            except Exception: pass
        self.ui_widgets = {}
        self.ui_handlers = {}
        try:
            if self.root is not None:
                self.ui_win_obj = tk.Toplevel(self.root)
            else:
                self.ui_win_obj = tk.Tk()
            self.ui_win_obj.title(title)
            self.ui_win_obj.geometry("%dx%d" % (w, h))
            self.ui_win_obj.configure(bg="#f0f0f0")
            self.ui_win_obj.update()
        except Exception as e:
            raise MiniError("uiwin 创建窗口失败：" + str(e))
        return None

    def _ui_place(self, args, fname):
        x = self._ui_args_num(args, 1, fname, "x")
        y = self._ui_args_num(args, 2, fname, "y")
        w = self._ui_args_num(args, 3, fname, "宽")
        h = self._ui_args_num(args, 4, fname, "高")
        return int(x), int(y), int(w), int(h)

    def ui_btn(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uibtn")
        if len(args) < 6:
            raise MiniError("uibtn 需要 6 个参数：(id, x, y, 宽, 高, 文字)")
        wid = self._ui_id(args, "uibtn")
        x, y, w, h = self._ui_place(args, "uibtn")
        text = str(args[5])
        try:
            b = tk.Button(self.ui_win_obj, text=text, font=("Microsoft YaHei UI", 10))
            b.place(x=x, y=y, width=w, height=h)
            self.ui_widgets[wid] = b
        except Exception as e:
            raise MiniError("uibtn 创建失败：" + str(e))
        return None

    def ui_label(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uilabel")
        if len(args) < 6:
            raise MiniError("uilabel 需要 6 个参数：(id, x, y, 宽, 高, 文字)")
        wid = self._ui_id(args, "uilabel")
        x, y, w, h = self._ui_place(args, "uilabel")
        text = str(args[5])
        try:
            lb = tk.Label(self.ui_win_obj, text=text, font=("Microsoft YaHei UI", 10), anchor="w", bg="#f0f0f0")
            lb.place(x=x, y=y, width=w, height=h)
            self.ui_widgets[wid] = lb
        except Exception as e:
            raise MiniError("uilabel 创建失败：" + str(e))
        return None

    def ui_input(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uiinput")
        if len(args) < 5:
            raise MiniError("uiinput 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uiinput")
        x, y, w, h = self._ui_place(args, "uiinput")
        try:
            e = tk.Entry(self.ui_win_obj, font=("Microsoft YaHei UI", 10))
            e.place(x=x, y=y, width=w, height=h)
            self.ui_widgets[wid] = e
        except Exception as e2:
            raise MiniError("uiinput 创建失败：" + str(e2))
        return None

    def ui_text(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uitext")
        if len(args) < 5:
            raise MiniError("uitext 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uitext")
        x, y, w, h = self._ui_place(args, "uitext")
        try:
            t = tk.Text(self.ui_win_obj, font=("Microsoft YaHei UI", 10), wrap="word")
            t.place(x=x, y=y, width=w, height=h)
            self.ui_widgets[wid] = t
        except Exception as e2:
            raise MiniError("uitext 创建失败：" + str(e2))
        return None

    def ui_check(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uicheck")
        if len(args) < 4:
            raise MiniError("uicheck 需要 4 个参数：(id, x, y, 文字)")
        wid = self._ui_id(args, "uicheck")
        x = self._ui_args_num(args, 1, "uicheck", "x")
        y = self._ui_args_num(args, 2, "uicheck", "y")
        text = str(args[3])
        try:
            var = tk.IntVar()
            cb = tk.Checkbutton(self.ui_win_obj, text=text, variable=var,
                                font=("Microsoft YaHei UI", 10), bg="#f0f0f0")
            cb.place(x=int(x), y=int(y))
            cb._hx_var = var
            self.ui_widgets[wid] = cb
        except Exception as e2:
            raise MiniError("uicheck 创建失败：" + str(e2))
        return None

    def ui_list(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uilist")
        if len(args) < 6:
            raise MiniError("uilist 需要 6 个参数：(id, x, y, 宽, 高, 选项数组)")
        wid = self._ui_id(args, "uilist")
        x, y, w, h = self._ui_place(args, "uilist")
        items = args[5]
        if not isinstance(items, list):
            raise MiniError("uilist 的第 6 个参数必须是数组")
        try:
            var = tk.StringVar()
            lb = tk.Listbox(self.ui_win_obj, font=("Microsoft YaHei UI", 10))
            for it in items:
                lb.insert("end", fmt(it))
            lb.place(x=x, y=y, width=w, height=h)
            self.ui_widgets[wid] = lb
        except Exception as e2:
            raise MiniError("uilist 创建失败：" + str(e2))
        return None

    def ui_range(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uirange")
        if len(args) < 5:
            raise MiniError("uirange 需要 5 个参数：(id, x, y, 宽, 最大值)")
        wid = self._ui_id(args, "uirange")
        x = self._ui_args_num(args, 1, "uirange", "x")
        y = self._ui_args_num(args, 2, "uirange", "y")
        w = self._ui_args_num(args, 3, "uirange", "宽")
        mx = self._ui_args_num(args, 4, "uirange", "最大值")
        try:
            sc = tk.Scale(self.ui_win_obj, from_=0, to=int(mx), orient="horizontal",
                          font=("Microsoft YaHei UI", 9))
            sc.place(x=int(x), y=int(y), width=int(w))
            self.ui_widgets[wid] = sc
        except Exception as e2:
            raise MiniError("uirange 创建失败：" + str(e2))
        return None

    def ui_progress(self, args):
        tk = self._ui_tk()
        self._ui_need_win("uiprogress")
        if len(args) < 5:
            raise MiniError("uiprogress 需要 5 个参数：(id, x, y, 宽, 高)")
        wid = self._ui_id(args, "uiprogress")
        x, y, w, h = self._ui_place(args, "uiprogress")
        try:
            pb = tk.Canvas(self.ui_win_obj, bg="#e0e0e0", highlightthickness=1,
                           highlightbackground="#cccccc")
            pb.place(x=x, y=y, width=w, height=h)
            pb._hx_rect = pb.create_rectangle(0, 0, 0, h, fill="#007acc", outline="")
            pb._hx_w = w
            pb._hx_h = h
            self.ui_widgets[wid] = pb
        except Exception as e2:
            raise MiniError("uiprogress 创建失败：" + str(e2))
        return None

    def ui_on(self, args):
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
        if event == "click":
            tk_event = "<Button-1>"
        elif event == "change":
            tk_event = "<KeyRelease>"
        elif event == "select":
            tk_event = "<<ListboxSelect>>"
        else:
            raise MiniError("uion 支持的事件：click / change / select")
        def handler(e):
            try:
                self.call(fn, [], 0)
            except Exception as ex:
                self._cb_errors.append(str(ex))
        try:
            w.bind(tk_event, handler)
        except Exception as ex:
            raise MiniError("uion 绑定失败：" + str(ex))
        return None

    def ui_get(self, args):
        wid = self._ui_id(args, "uiget")
        if wid not in self.ui_widgets:
            raise MiniError("uiget 找不到组件 " + wid)
        w = self.ui_widgets[wid]
        tk = self._ui_tk()
        try:
            if isinstance(w, tk.Entry):
                return w.get()
            if isinstance(w, tk.Text):
                return w.get("1.0", "end-1c")
            if isinstance(w, tk.Checkbutton):
                return bool(w._hx_var.get())
            if isinstance(w, tk.Scale):
                return float(w.get())
            if isinstance(w, tk.Listbox):
                sel = w.curselection()
                return w.get(sel[0]) if sel else ""
            if isinstance(w, tk.Canvas) and hasattr(w, "_hx_rect"):
                return getattr(w, "_hx_value", 0)
            if isinstance(w, tk.Label):
                return w.cget("text")
            if isinstance(w, tk.Button):
                return w.cget("text")
        except Exception as ex:
            raise MiniError("uiget 失败：" + str(ex))
        return ""

    def ui_set(self, args):
        if len(args) < 2:
            raise MiniError("uiset 需要 2 个参数：(组件id, 值)")
        wid = self._ui_id(args, "uiset")
        if wid not in self.ui_widgets:
            raise MiniError("uiset 找不到组件 " + wid)
        w = self.ui_widgets[wid]
        val = args[1]
        tk = self._ui_tk()
        try:
            if isinstance(w, tk.Entry):
                w.delete(0, "end"); w.insert(0, fmt(val))
            elif isinstance(w, tk.Text):
                w.delete("1.0", "end"); w.insert("1.0", fmt(val))
            elif isinstance(w, tk.Checkbutton):
                w._hx_var.set(1 if truth(val) else 0)
            elif isinstance(w, tk.Scale):
                w.set(float(val) if self._is_num(val) else 0)
            elif isinstance(w, tk.Listbox):
                w.delete(0, "end")
                if isinstance(val, list):
                    for it in val: w.insert("end", fmt(it))
            elif isinstance(w, tk.Canvas) and hasattr(w, "_hx_rect"):
                pct = float(val) if self._is_num(val) else 0
                if pct < 0: pct = 0
                if pct > 100: pct = 100
                w._hx_value = pct
                ww = w._hx_w * pct / 100.0
                w.coords(w._hx_rect, 0, 0, ww, w._hx_h)
            elif isinstance(w, (tk.Label, tk.Button)):
                w.configure(text=fmt(val))
        except Exception as ex:
            raise MiniError("uiset 失败：" + str(ex))
        return None

    def ui_run(self, args):
        self._ui_need_win("uirun")
        self.ui_running = True
        err = None
        try:
            self.ui_win_obj.update()
            while True:
                self.ui_win_obj.update()
                time.sleep(0.02)
                self._check_cb_errors()
                if not self.ui_win_obj.winfo_exists():
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
  'uilabel("id", x, y, 宽, 高, "文字");   标签',
  'uibtn("id", x, y, 宽, 高, "按钮");     按钮',
  'uiinput("id", x, y, 宽, 高);           单行输入框',
  'uitext("id", x, y, 宽, 高);            多行文本',
  'uicheck("id", x, y, "选项");           勾选框',
  'uilist("id", x, y, 宽, 高, ["a","b"]); 列表',
  'uirange("id", x, y, 宽, 100);          滑块（0 到最大值）',
  'uiprogress("id", x, y, 宽, 高);        进度条',
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

CHEAT_ORDER = ["变量","输出与输入","函数","控制流","运算符","数组","字典","字符串","界面","图形","交互","文件与系统","注释"]

def cheatsheet_text():
    lines = []
    for sec in CHEAT_ORDER:
        lines.append("【%s】" % sec)
        for item in CHEATSHEET[sec]:
            lines.append("  " + item)
        lines.append("")
    return "\n".join(lines)

SAMPLE = '''# HX 语言示例：print(...) 直接输出
fib(n) {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}
add(a, b) { return a + b; }

print("fib(10) =", fib(10));
print("add(3,4) =", add(3, 4));

n = 42;
print("type(n) =", type(n), "| n =", n);
s = "hi";
print("type(s) =", type(s));
arr2 = [1, 2];
print("type(arr2) =", type(arr2));
print("括号 print 更清晰");

arr = [1, 2, 3];
push(arr, 4);
print("arr =", arr, "len =", len(arr));

d = {name: "mini", ver: 2};
print("dict =", d, "name =", d.name, "ver =", d["ver"]);

i = 0;
sum = 0;
while (i < len(arr)) { sum = sum + arr[i]; i = i + 1; }
print("sum =", sum);

for (j = 0; j < len(arr); j += 1) { print("项:", arr[j]); }
for (k = 0; k < 3; k += 1) { print("k =", k); }

s = "hi";
print(s + "!" + 1);
if (sum > 5 and true) { print("ok"); } else { print("bad"); }
'''

TOKRE = re.compile(r'#[^\n]*|"[^"\n]*"|\'[^\'\n]*\'|\b\d+(?:\.\d+)?\b|\b(?:if|elif|else|while|for|return|true|false|null|and|or|not|try|catch|break|continue|del)\b|\b(?:print|len|push|keys|str|num|range|input|help|type)\b')
KW = {"if","else","elif","while","for","break","continue","del","return","true","false","null","and","or","not","try","catch"}


def idx_of(txt,off):
    line=txt.count("\n",0,off)+1
    col=off-(txt.rfind("\n",0,off)+1)
    return "%d.%d" % (line,col)


def hl(w):
    txt=w.get("1.0","end-1c")
    for t in ("kw","str","num","cmt","bi"):
        w.tag_remove(t,"1.0","end")
    for m in TOKRE.finditer(txt):
        s=m.group()
        if s[0]=="#": t="cmt"
        elif s[0] in "\"'": t="str"
        elif s[0].isdigit(): t="num"
        elif s in KW: t="kw"
        else: t="bi"
        w.tag_add(t,idx_of(txt,m.start()),idx_of(txt,m.end()))


BG="#1e1e1e"; PANEL="#252526"; FG="#d4d4d4"
TOOLBAR_BG="#2d2d30"; BORDER="#3e3e42"; ACCENT="#0e639c"; ACCENT_HOVER="#1177bb"
GUTTER_BG="#1e1e1e"; GUTTER_FG="#858585"; STATUS_BG="#007acc"; STATUS_FG="#ffffff"
ERR_RED="#f14c4c"

LN_FONT=("Consolas",12)
UI_FONT=("Microsoft YaHei UI",9)


AI_CONFIG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "HXLanguage")
AI_CONFIG_PATH = os.path.join(AI_CONFIG_DIR, "config.json")
FENCE = chr(96) * 3

AI_SYSTEM_PROMPT = (
    "你叫小智，是 HX 语言（源文件后缀 .hxg）的编程向导，帮助用户在 HX 语言的编程世界里闯荡。\n\n"
    "HX 语言语法要点：\n"
    "- 变量直接赋值即声明，自动推断类型：x = 10;  s = \"hi\";  arr = [1,2,3];  d = {a:1};\n"
    "- 函数（C 风格）：add(a, b) { return a + b; }  没有 fn 关键字\n"
    "- 条件：if (c) { } else if (c2) { } else { }（没有 elif）\n"
    "- 循环：while (c) { }  /  for (i = 0; i < n; i += 1) { }  没有 for-in\n"
    "- 异常：try { } catch (e) { }\n"
    "- 字符串插值：\"hi \u0024{x}\"\n"
    "- print 必须加括号：print(\"hi\", 1);\n"
    "- 输入：input(\"提示\") 返回字符串；scanf(\"%d %d\", a, b) 按格式读入（变量需先声明）\n"
    "- 内置：type(x) 查类型、len、push、min、max、abs、range、keys、items、has、set、upper、lower、trim、split、join、str、num、input、help\n"
    "- 逻辑运算：&& || ! （也支持 and or not）\n"
    "- 图形：gwin(w,h,title) 建窗口、gline(x1,y1,x2,y2,color,width)、grect(x1,y1,x2,y2,color,fill)、"
    "gcircle(cx,cy,r,color,fill)、gtext(x,y,text,color)、gclear()、gsleep(ms) 刷新并暂停\n"
    "- 交互：gwaitkey() 等按键返回键名、gwaitclick() 等点击返回 [x,y]、"
    "gkeydown(fn) 按键回调、gclick(fn) 点击回调\n"
    "- 文件：readfile(p)、writefile(p,s)、appendfile(p,s)、exists(p)、files(dir)\n"
    "- 系统：openfile(p) 打开文件、openurl(u) 开浏览器、runapp(cmd) 启程序\n"
    "- 注释用 #，语句末尾分号可省\n"
    "- 图形界面（需要写 GUI 时用）：uiwin(w,h,title) 建窗口、uibtn(id,x,y,w,h,text) 按钮、"
    "uilabel(id,x,y,w,h,text) 标签、uiinput(id,x,y,w,h) 输入框、uitext(id,x,y,w,h) 多行文本、"
    "uicheck(id,x,y,text) 勾选框、uilist(id,x,y,w,h,items) 列表、uirange(id,x,y,w,max) 滑块、"
    "uiprogress(id,x,y,w,h) 进度条；uion(id,\"click\",fn) 绑事件、uiget(id) 读值、uiset(id,v) 设值、"
    "uirun() 启动界面\n\n"
    "回答要简洁、直接给可运行的 HX 代码，用 " + FENCE + "hxg 代码块包裹。"
)


def ai_load_config():
    try:
        with open(AI_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    return {"base_url": cfg.get("base_url", ""),
            "api_key": cfg.get("api_key", ""),
            "model": cfg.get("model", "")}


def ai_save_config(cfg):
    try:
        os.makedirs(AI_CONFIG_DIR, exist_ok=True)
        with open(AI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def ai_chat_stream(cfg, messages, on_chunk):
    """流式请求；每个增量片段调用 on_chunk(text)，返回完整文本。"""
    url = (cfg.get("base_url") or "").rstrip("/")
    if not url:
        raise ValueError("Base URL 未配置")
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    payload = {
        "model": cfg.get("model") or "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": AI_SYSTEM_PROMPT}] + list(messages),
        "temperature": 0.7,
        "stream": True,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("Authorization", "Bearer " + (cfg.get("api_key") or ""))
    full = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", "replace").strip()
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
            except Exception:
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            piece = delta.get("content")
            if piece:
                full.append(piece)
                try: on_chunk(piece)
                except Exception: pass
    return "".join(full)


def ai_chat(cfg, messages):
    url = (cfg.get("base_url") or "").rstrip("/")
    if not url:
        raise ValueError("Base URL 未配置")
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    payload = {
        "model": cfg.get("model") or "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": AI_SYSTEM_PROMPT}] + list(messages),
        "temperature": 0.7,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + (cfg.get("api_key") or ""))
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8", "replace")
    body = json.loads(raw)
    if "choices" not in body or not body["choices"]:
        raise ValueError("响应格式异常：" + raw[:200])
    return body["choices"][0]["message"]["content"]


UI_COMPONENTS = [
    ("button", "按钮", 6, ["id", "x", "y", "w", "h", "text"]),
    ("label", "标签", 6, ["id", "x", "y", "w", "h", "text"]),
    ("input", "输入框", 5, ["id", "x", "y", "w", "h"]),
    ("text", "多行文本", 5, ["id", "x", "y", "w", "h"]),
    ("check", "勾选框", 4, ["id", "x", "y", "text"]),
    ("list", "下拉列表", 6, ["id", "x", "y", "w", "h", "items"]),
    ("range", "滑块", 5, ["id", "x", "y", "w", "max"]),
    ("progress", "进度条", 5, ["id", "x", "y", "w", "h"]),
]


def ui_parse_code(text):
    """从 HX 源码里解析 ui* 调用，还原成设计器组件列表"""
    import re as _re
    items = []
    next_id = 1
    def nid():
        nonlocal next_id
        r = "w%d" % next_id
        next_id += 1
        return r
    def num(v, d=0):
        try:
            return int(float(str(v).strip()))
        except Exception:
            return d

    # 去掉注释
    lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("#"):
            continue
        lines.append(ln)

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        # 按钮 uibtn("id", x, y, w, h, "text")
        m = _re.match(r'uibtn\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*"([^"]*)"\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "button",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 100), "h": num(m.group(5), 32), "text": m.group(6)}})
            continue
        m = _re.match(r'uilabel\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*"([^"]*)"\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "label",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 120), "h": num(m.group(5), 26), "text": m.group(6)}})
            continue
        m = _re.match(r'uiinput\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "input",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 180), "h": num(m.group(5), 28)}})
            continue
        m = _re.match(r'uitext\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "text",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 200), "h": num(m.group(5), 100)}})
            continue
        m = _re.match(r'uicheck\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*"([^"]*)"\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "check",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "text": m.group(4)}})
            continue
        m = _re.match(r'uilist\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),', s)
        if m:
            items.append({"id": m.group(1), "kind": "list",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 150), "h": num(m.group(5), 100)}})
            continue
        m = _re.match(r'uirange\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,\)]+)', s)
        if m:
            items.append({"id": m.group(1), "kind": "range",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 180), "max": num(m.group(5), 100)}})
            continue
        m = _re.match(r'uiprogress\s*\(\s*"([^"]*)"\s*,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)\s*\)', s)
        if m:
            items.append({"id": m.group(1), "kind": "progress",
                          "props": {"id": m.group(1), "x": num(m.group(2)), "y": num(m.group(3)),
                                    "w": num(m.group(4), 200), "h": num(m.group(5), 20)}})
            continue
    return items


def ui_gen_code(items):
    lines = ["# ===== 由 UI 设计器生成 ====="]
    if not items:
        lines.append("# （还没有添加组件）")
        return "\n".join(lines)
    # 计算窗口尺寸
    max_x = 0; max_y = 0
    for it in items:
        w = it["props"].get("w", 100); h = it["props"].get("h", 30)
        x = it["props"].get("x", 0); y = it["props"].get("y", 0)
        max_x = max(max_x, x + w); max_y = max(max_y, y + h)
    win_w = max(400, max_x + 30); win_h = max(300, max_y + 40)
    title = "我的界面"
    lines.append('uiwin(%d, %d, "%s");' % (win_w, win_h, title))
    lines.append("")
    for it in items:
        kind = it["kind"]
        p = it["props"]
        wid = p.get("id", "w1")
        if kind == "button":
            lines.append('# 按钮 %s' % wid)
            lines.append('uibtn("%s", %d, %d, %d, %d, "%s");'
                         % (wid, p["x"], p["y"], p["w"], p["h"], p.get("text", "按钮")))
        elif kind == "label":
            lines.append('# 标签 %s' % wid)
            lines.append('uilabel("%s", %d, %d, %d, %d, "%s");'
                         % (wid, p["x"], p["y"], p["w"], p["h"], p.get("text", "标签")))
        elif kind == "input":
            lines.append('# 输入框 %s' % wid)
            lines.append('uiinput("%s", %d, %d, %d, %d);'
                         % (wid, p["x"], p["y"], p["w"], p["h"]))
        elif kind == "text":
            lines.append('# 多行文本 %s' % wid)
            lines.append('uitext("%s", %d, %d, %d, %d);'
                         % (wid, p["x"], p["y"], p["w"], p["h"]))
        elif kind == "check":
            lines.append('# 勾选框 %s' % wid)
            lines.append('uicheck("%s", %d, %d, "%s");'
                         % (wid, p["x"], p["y"], p.get("text", "选项")))
        elif kind == "list":
            lines.append('# 下拉列表 %s' % wid)
            lines.append('uilist("%s", %d, %d, %d, %d, ["选项1", "选项2"]);'
                         % (wid, p["x"], p["y"], p["w"], p["h"]))
        elif kind == "range":
            lines.append('# 滑块 %s' % wid)
            lines.append('uirange("%s", %d, %d, %d, %d);'
                         % (wid, p["x"], p["y"], p["w"], p.get("max", 100)))
        elif kind == "progress":
            lines.append('# 进度条 %s' % wid)
            lines.append('uiprogress("%s", %d, %d, %d, %d);'
                         % (wid, p["x"], p["y"], p["w"], p["h"]))
        lines.append("")
    lines.append("# 事件处理示例（按需修改）")
    lines.append("on_click() {")
    lines.append('    print("按钮被点击");')
    lines.append("}")
    lines.append("")
    lines.append("# 启动界面")
    lines.append("uirun();")
    return "\n".join(lines)


def open_ui_designer(root, ed, hl_fn, sync_fn, initial_items=None):
    """打开 UI 设计器窗口"""
    import tkinter as tk
    from tkinter import messagebox

    BG2 = "#1e1e1e"; PANEL2 = "#252526"; HEAD2 = "#2d2d30"; FG2 = "#cccccc"
    BORDER2 = "#3e3e42"; ACCENT2 = "#0e639c"; SELECT = "#094771"
    UIF = ("Microsoft YaHei UI", 9)

    win = tk.Toplevel(root)
    win.title("UI 设计器")
    win.geometry("1000x680")
    win.configure(bg=BG2)
    win.transient(root)

    items = list(initial_items) if initial_items else []
    max_id = 0
    for it in items:
        try:
            n = int(str(it["id"]).lstrip("w"))
            if n > max_id: max_id = n
        except Exception:
            pass
    state = {"kind": None, "sel": None, "next_id": max_id + 1}

    # ---------- 左侧组件面板 ----------
    left = tk.Frame(win, bg=PANEL2, width=160)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)
    tk.Label(left, text="组件", bg=HEAD2, fg="#9cdcfe", font=("Microsoft YaHei UI", 10, "bold"),
             pady=8).pack(fill="x")
    palette_btns = {}
    for kind, label, _, _ in UI_COMPONENTS:
        b = tk.Label(left, text="  " + label, bg=PANEL2, fg=FG2, font=UIF,
                     anchor="w", padx=10, pady=6, cursor="hand2")
        b.pack(fill="x")
        b.bind("<Button-1>", lambda e, k=kind: pick_component(k))
        b.bind("<Enter>", lambda e, w=b: w.configure(bg="#2a2d2e"))
        b.bind("<Leave>", lambda e, w=b: w.configure(bg=PANEL2 if state["kind"] != b._k else SELECT) if hasattr(b, "_k") else w.configure(bg=PANEL2))
        b._k = kind
        palette_btns[kind] = b

    def pick_component(kind):
        state["kind"] = kind
        for k, b in palette_btns.items():
            b.configure(bg=SELECT if k == kind else PANEL2,
                        fg="#ffffff" if k == kind else FG2)
        status.configure(text="点击画布放置 " + dict((c[0], c[1]) for c in UI_COMPONENTS)[kind])

    # ---------- 中间画布 ----------
    center = tk.Frame(win, bg=BG2)
    center.pack(side="left", fill="both", expand=True)
    canvas_head = tk.Frame(center, bg=HEAD2, height=32)
    canvas_head.pack(fill="x"); canvas_head.pack_propagate(False)
    tk.Label(canvas_head, text="画布（点击放置组件，拖动调整位置，Delete 删除）",
             bg=HEAD2, fg="#858585", font=UIF).pack(side="left", padx=10, pady=6)

    canvas_wrap = tk.Frame(center, bg=BG2)
    canvas_wrap.pack(fill="both", expand=True, padx=12, pady=12)
    canvas = tk.Canvas(canvas_wrap, bg="#f0f0f0", highlightthickness=1,
                       highlightbackground=BORDER2)
    canvas.pack(fill="both", expand=True)

    drag = {"item": None, "ox": 0, "oy": 0}

    # ---------- 右侧属性面板 ----------
    right = tk.Frame(win, bg=PANEL2, width=220)
    right.pack(side="right", fill="y")
    right.pack_propagate(False)
    tk.Label(right, text="属性", bg=HEAD2, fg="#9cdcfe", font=("Microsoft YaHei UI", 10, "bold"),
             pady=8).pack(fill="x")
    prop_frame = tk.Frame(right, bg=PANEL2)
    prop_frame.pack(fill="both", expand=True, padx=10, pady=10)

    prop_entries = {}

    def redraw():
        canvas.delete("all")
        for it in items:
            p = it["props"]
            x, y = p["x"], p["y"]
            w = p.get("w", 100); h = p.get("h", 30)
            kind = it["kind"]
            outline = "#ff8c00" if it is state["sel"] else "#888888"
            width = 2 if it is state["sel"] else 1
            if kind == "button":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#e1e1e1", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + w / 2, y + h / 2, text=p.get("text", "按钮"), fill="#000", tags=("comp", it["id"]))
            elif kind == "label":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#f0f0f0", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + 6, y + h / 2, text=p.get("text", "标签"), fill="#000", anchor="w", tags=("comp", it["id"]))
            elif kind == "input":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#ffffff", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + 6, y + h / 2, text="输入框", fill="#999", anchor="w", tags=("comp", it["id"]))
            elif kind == "text":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#ffffff", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + 6, y + 12, text="多行文本", fill="#999", anchor="w", tags=("comp", it["id"]))
            elif kind == "check":
                canvas.create_rectangle(x, y, x + 14, y + 14, fill="#ffffff", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + 20, y + 7, text=p.get("text", "选项"), fill="#000", anchor="w", tags=("comp", it["id"]))
            elif kind == "list":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#ffffff", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + 6, y + 10, text="列表", fill="#999", anchor="w", tags=("comp", it["id"]))
            elif kind == "range":
                canvas.create_rectangle(x, y, x + w, y + 20, fill="#e8e8e8", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_text(x + w / 2, y + 10, text="滑块 0-" + str(p.get("max", 100)), fill="#000", tags=("comp", it["id"]))
            elif kind == "progress":
                canvas.create_rectangle(x, y, x + w, y + h, fill="#e0e0e0", outline=outline, width=width, tags=("comp", it["id"]))
                canvas.create_rectangle(x, y, x + w * 0.4, y + h, fill="#007acc", outline="", tags=("comp", it["id"]))
        # 网格
        cw = canvas.winfo_width() or 600
        ch = canvas.winfo_height() or 500
        for gx in range(0, cw, 20):
            canvas.create_line(gx, 0, gx, ch, fill="#e8e8e8", tags=("grid",))
        for gy in range(0, ch, 20):
            canvas.create_line(0, gy, cw, gy, fill="#e8e8e8", tags=("grid",))
        canvas.tag_lower("grid")

    def refresh_props():
        for w in prop_frame.winfo_children():
            w.destroy()
        prop_entries.clear()
        sel = state["sel"]
        if sel is None:
            tk.Label(prop_frame, text="选中组件后\n在这里编辑属性", bg=PANEL2, fg="#858585",
                     font=UIF, justify="left").pack(anchor="w")
            return
        kind = sel["kind"]; p = sel["props"]
        info = [c for c in UI_COMPONENTS if c[0] == kind][0]
        tk.Label(prop_frame, text=info[1] + "（" + p["id"] + "）", bg=PANEL2, fg="#9cdcfe",
                 font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        fields = info[3]
        for f in fields:
            tk.Label(prop_frame, text=f, bg=PANEL2, fg="#858585", font=UIF).pack(anchor="w", pady=(4, 0))
            e = tk.Entry(prop_frame, bg="#3c3c3c", fg=FG2, insertbackground=FG2,
                         relief="flat", bd=0, font=("Consolas", 10), highlightthickness=0)
            val = p.get(f, "")
            if isinstance(val, list):
                val = ",".join(str(v) for v in val)
            e.insert(0, str(val))
            e.pack(fill="x", pady=(2, 0))
            prop_entries[f] = e

        def apply_props(e=None):
            for f, entry in prop_entries.items():
                v = entry.get()
                if f in ("x", "y", "w", "h", "max"):
                    try:
                        p[f] = int(float(v))
                    except Exception:
                        pass
                elif f == "items":
                    p[f] = [s.strip() for s in v.split(",") if s.strip()]
                else:
                    p[f] = v
            redraw()

        for e in prop_entries.values():
            e.bind("<KeyRelease>", apply_props)
            e.bind("<FocusOut>", apply_props)
        tk.Button(prop_frame, text="删除此组件", command=lambda: delete_selected(),
                  bg="#8b0000", fg="#ffffff", relief="flat", bd=0, font=UIF,
                  padx=10, pady=4, cursor="hand2").pack(fill="x", pady=(16, 0))

    def select_item(it):
        state["sel"] = it
        refresh_props()
        redraw()

    def delete_selected():
        if state["sel"] is None: return
        items.remove(state["sel"])
        state["sel"] = None
        refresh_props()
        redraw()

    def on_canvas_click(e):
        x, y = e.x, e.y
        # 先检查是否点中已有组件
        hit = None
        for it in reversed(items):
            p = it["props"]
            w = p.get("w", 100) if it["kind"] in ("button", "label", "input", "text", "list", "progress") else 160
            h = p.get("h", 30) if it["kind"] in ("button", "label", "input", "text", "list", "progress") else 20
            if p["x"] <= x <= p["x"] + w and p["y"] <= y <= p["y"] + h:
                hit = it
                break
        if hit is not None:
            select_item(hit)
            return
        # 否则放置新组件
        if state["kind"] is None:
            select_item(None)
            return
        kind = state["kind"]
        wid = "w%d" % state["next_id"]
        state["next_id"] += 1
        defaults = {
            "button": {"w": 100, "h": 32, "text": "按钮"},
            "label": {"w": 120, "h": 26, "text": "标签"},
            "input": {"w": 180, "h": 28},
            "text": {"w": 200, "h": 100},
            "check": {"text": "选项"},
            "list": {"w": 150, "h": 100},
            "range": {"w": 180, "max": 100},
            "progress": {"w": 200, "h": 20},
        }.get(kind, {})
        props = {"id": wid, "x": x, "y": y}
        props.update(defaults)
        it = {"id": wid, "kind": kind, "props": props}
        items.append(it)
        select_item(it)
        redraw()
        status.configure(text="已添加 " + wid)

    def on_press(e):
        hit = None
        for it in reversed(items):
            p = it["props"]
            w = p.get("w", 100) if it["kind"] in ("button", "label", "input", "text", "list", "progress") else 160
            h = p.get("h", 30) if it["kind"] in ("button", "label", "input", "text", "list", "progress") else 20
            if p["x"] <= e.x <= p["x"] + w and p["y"] <= e.y <= p["y"] + h:
                hit = it
                break
        if hit is not None:
            select_item(hit)
            drag["item"] = hit
            drag["ox"] = e.x - hit["props"]["x"]
            drag["oy"] = e.y - hit["props"]["y"]

    def on_drag(e):
        if drag["item"] is None: return
        drag["item"]["props"]["x"] = max(0, e.x - drag["ox"])
        drag["item"]["props"]["y"] = max(0, e.y - drag["oy"])
        redraw()

    def on_release(e):
        drag["item"] = None

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Double-Button-1>", on_canvas_click)
    canvas.bind("<Configure>", lambda e: redraw())
    win.bind("<Delete>", lambda e: delete_selected())

    # ---------- 底部状态栏 + 生成 ----------
    status = tk.Label(win, text="从左侧选组件，双击画布放置", bg=HEAD2, fg="#858585",
                      font=UIF, anchor="w", padx=10, pady=4)
    status.pack(side="bottom", fill="x")

    btn_bar = tk.Frame(win, bg=HEAD2)
    btn_bar.pack(side="bottom", fill="x", pady=(0, 1))

    def do_generate():
        code = ui_gen_code(items)
        ed.insert("insert", "\n" + code + "\n")
        try:
            hl_fn(ed)
            sync_fn()
        except Exception:
            pass
        status.configure(text="代码已插入编辑器（共 %d 个组件）" % len(items))
        messagebox.showinfo("生成完成", "代码已插入到编辑器当前光标位置。")

    def do_preview():
        if not items:
            messagebox.showinfo("提示", "还没有添加组件")
            return
        code = ui_gen_code(items)
        import tempfile
        p = os.path.join(tempfile.gettempdir(), "_ui_preview.hxg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), p])
        except Exception as ex:
            messagebox.showerror("预览失败", str(ex))

    tk.Button(btn_bar, text="生成代码", command=do_generate,
              bg=ACCENT2, fg="#ffffff", relief="flat", bd=0, font=UIF,
              padx=16, pady=6, cursor="hand2").pack(side="right", padx=8, pady=6)
    tk.Button(btn_bar, text="运行预览", command=do_preview,
              bg="#3a3a3d", fg=FG2, relief="flat", bd=0, font=UIF,
              padx=16, pady=6, cursor="hand2").pack(side="right", pady=6)

    def do_import():
        code = ed.get("1.0", "end-1c")
        parsed = ui_parse_code(code)
        if not parsed:
            messagebox.showinfo("提示", "当前编辑器里没有找到 ui* 组件代码")
            return
        items.clear()
        items.extend(parsed)
        max_id = 0
        for it in items:
            try:
                n = int(str(it["id"]).lstrip("w"))
                if n > max_id: max_id = n
            except Exception:
                pass
        state["next_id"] = max_id + 1
        state["sel"] = None
        refresh_props()
        redraw()
        status.configure(text="已从编辑器导入 %d 个组件" % len(items))

    tk.Button(btn_bar, text="从编辑器导入", command=do_import,
              bg="#3a3a3d", fg=FG2, relief="flat", bd=0, font=UIF,
              padx=16, pady=6, cursor="hand2").pack(side="right", padx=(0, 8), pady=6)

    redraw()
    refresh_props()


def build_gui(initial_path=None):
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox

    project_dir = os.path.dirname(os.path.abspath(__file__))

    BG="#1e1e1e"; SIDEBAR="#252526"; ACTIVITY="#333333"; TAB_BG="#2d2d2d"
    TAB_ACTIVE="#1e1e1e"; FG="#cccccc"; FG_DIM="#858585"
    BORDER="#2d2d2d"; BORDER2="#3e3e42"; ACCENT="#0e639c"; ACCENT_HOVER="#1177bb"
    STATUS_BG="#007acc"; STATUS_FG="#ffffff"; ERR_RED="#f14c4c"
    GUTTER_BG="#1e1e1e"; GUTTER_FG="#858585"; PANEL="#1e1e1e"; PANEL_HEAD="#252526"

    root=tk.Tk()
    root.title("HX Studio")
    root.geometry("1360x880")
    root.configure(bg=BG)
    root.minsize(900,600)

    hooks={"sync": lambda: None}
    err={"line":0,"col":0}
    st={"trace":[],"i":-1,"it":None}
    cur={"path":None}
    ui={"sidebar_visible":True,"active_activity":"files"}

    menubar=tk.Menu(root,bg=TAB_BG,fg=FG,activebackground=ACCENT,activeforeground="#ffffff",tearoff=0,font=UI_FONT)
    mopt=dict(tearoff=0,bg=TAB_BG,fg=FG,activebackground=ACCENT,activeforeground="#ffffff",font=UI_FONT)
    fm=tk.Menu(menubar,**mopt)
    fm.add_command(label="新建文件        Ctrl+N",command=lambda: do_new())
    fm.add_command(label="打开文件…       Ctrl+O",command=lambda: do_open())
    fm.add_command(label="保存            Ctrl+S",command=lambda: do_save())
    fm.add_command(label="另存为…",command=lambda: do_save_as())
    fm.add_separator()
    fm.add_command(label="退出",command=lambda: root.destroy())
    menubar.add_cascade(label="文件",menu=fm)
    em=tk.Menu(menubar,**mopt)
    em.add_command(label="撤销",command=lambda: (ed.event_generate("<<Undo>>"),"break")[1])
    em.add_command(label="重做",command=lambda: (ed.event_generate("<<Redo>>"),"break")[1])
    em.add_separator()
    em.add_command(label="清空编辑器",command=lambda: do_clear())
    menubar.add_cascade(label="编辑",menu=em)
    rm=tk.Menu(menubar,**mopt)
    rm.add_command(label="运行            F5",command=lambda: do_run())
    rm.add_command(label="单步            F10",command=lambda: do_step())
    rm.add_command(label="上一步",command=lambda: do_prev())
    rm.add_separator()
    rm.add_command(label="载入示例",command=lambda: do_sample())
    menubar.add_cascade(label="运行",menu=rm)
    vm=tk.Menu(menubar,**mopt)
    vm.add_command(label="切换侧边栏      Ctrl+B",command=lambda: toggle_sidebar())
    vm.add_command(label="显示/隐藏 小智",command=lambda: toggle_ai())
    vm.add_separator()
    vm.add_command(label="UI 设计器        Ctrl+U",command=lambda: open_ui_designer(root,ed,hl,sync_editor))
    vm.add_command(label="从编辑器代码加载到设计器",command=lambda: load_ui_from_editor())
    menubar.add_cascade(label="视图",menu=vm)
    hm=tk.Menu(menubar,**mopt)
    hm.add_command(label="语法速查",command=lambda: do_cheat())
    hm.add_command(label="关于 HX Studio",command=lambda: messagebox.showinfo("关于","HX Studio\nHX 语言集成开发环境\n\n内置小智 AI 助手"))
    menubar.add_cascade(label="帮助",menu=hm)
    root.config(menu=menubar)

    body=tk.Frame(root,bg=BG)
    body.pack(fill="both",expand=True)

    ai_panel=tk.Frame(body,bg=SIDEBAR,width=380)
    ai_panel.pack(side="right",fill="y")
    ai_panel.pack_propagate(False)
    ai_divider=tk.Frame(body,bg=BORDER,width=1)
    ai_divider.pack(side="right",fill="y")

    activity=tk.Frame(body,bg=ACTIVITY,width=48)
    activity.pack(side="left",fill="y")
    activity.pack_propagate(False)

    sidebar=tk.Frame(body,bg=SIDEBAR,width=220)
    sidebar.pack(side="left",fill="y")
    sidebar.pack_propagate(False)
    sb_divider=tk.Frame(body,bg=BORDER,width=1)
    sb_divider.pack(side="left",fill="y")

    main=tk.Frame(body,bg=BG)
    main.pack(side="left",fill="both",expand=True)

    def toggle_sidebar():
        if ui["sidebar_visible"]:
            sidebar.pack_forget(); sb_divider.pack_forget(); ui["sidebar_visible"]=False
        else:
            sidebar.pack(side="left",fill="y",after=activity)
            sb_divider.pack(side="left",fill="y",after=sidebar)
            ui["sidebar_visible"]=True
    def toggle_ai():
        if ai_panel.winfo_ismapped():
            ai_panel.pack_forget(); ai_divider.pack_forget()
        else:
            ai_panel.pack(side="right",fill="y"); ai_divider.pack(side="right",fill="y")

    act_btns={}
    def add_activity(icon,name):
        f=tk.Frame(activity,bg=ACTIVITY,height=48)
        f.pack(fill="x")
        lbl=tk.Label(f,text=icon,bg=ACTIVITY,fg="#858585",font=("Segoe UI Emoji",17),cursor="hand2",pady=8)
        lbl.pack(fill="both",expand=True)
        act_btns[name]=(f,lbl)
        lbl.bind("<Enter>",lambda e: lbl.configure(fg="#ffffff") if ui["active_activity"]!=name else None)
        lbl.bind("<Leave>",lambda e: lbl.configure(fg="#858585") if ui["active_activity"]!=name else None)
        lbl.bind("<Button-1>",lambda e: set_activity(name))
    def set_activity(name):
        ui["active_activity"]=name
        for k,(f,l) in act_btns.items():
            l.configure(fg="#ffffff" if k==name else "#858585")
        if name=="files": show_explorer()
        elif name=="search": show_search()
        elif name=="ai": toggle_ai()
        elif name=="settings": ai_config_dialog()
        if not sidebar.winfo_ismapped():
            sidebar.pack(side="left",fill="y",after=activity)
            sb_divider.pack(side="left",fill="y",after=sidebar)
            ui["sidebar_visible"]=True

    add_activity("📄","files")
    add_activity("🔍","search")
    add_activity("🤖","ai")
    add_activity("⚙","settings")

    sidebar_title=tk.Frame(sidebar,bg=SIDEBAR,height=35)
    sidebar_title.pack(fill="x"); sidebar_title.pack_propagate(False)
    sidebar_title_lbl=tk.Label(sidebar_title,text="资源管理器",bg=SIDEBAR,fg="#bbbbbb",font=("Microsoft YaHei UI",9,"bold"),anchor="w",padx=12)
    sidebar_title_lbl.pack(fill="both",expand=True)

    sidebar_body=tk.Frame(sidebar,bg=SIDEBAR)
    sidebar_body.pack(fill="both",expand=True)
    file_list=tk.Frame(sidebar_body,bg=SIDEBAR)
    search_box=tk.Frame(sidebar_body,bg=SIDEBAR)

    def show_explorer():
        sidebar_title_lbl.configure(text="资源管理器")
        search_box.pack_forget(); file_list.pack(fill="both",expand=True)
        refresh_explorer()
    def show_search():
        sidebar_title_lbl.configure(text="搜索")
        file_list.pack_forget(); search_box.pack(fill="both",expand=True)
        for w in search_box.winfo_children(): w.destroy()
        tk.Label(search_box,text="搜索文件",bg=SIDEBAR,fg=FG_DIM,font=UI_FONT,anchor="w",padx=12,pady=8).pack(fill="x")
        ent=tk.Entry(search_box,bg="#3c3c3c",fg=FG,insertbackground=FG,relief="flat",bd=0,font=("Consolas",10),highlightthickness=0)
        ent.pack(fill="x",padx=12,pady=4)
        res_list=tk.Frame(search_box,bg=SIDEBAR); res_list.pack(fill="both",expand=True,pady=4)
        def do_search(e=None):
            for w in res_list.winfo_children(): w.destroy()
            kw=ent.get().strip().lower()
            try: files=sorted([f for f in os.listdir(project_dir) if f.endswith(".hxg")])
            except Exception: files=[]
            for f in files:
                if kw and kw not in f.lower(): continue
                lab=tk.Label(res_list,text="  📄 "+f,bg=SIDEBAR,fg=FG,font=UI_FONT,anchor="w",cursor="hand2")
                lab.pack(fill="x")
                lab.bind("<Button-1>",lambda e,fn=f: open_file(os.path.join(project_dir,fn)))
                lab.bind("<Enter>",lambda e,l=lab: l.configure(bg="#2a2d2e"))
                lab.bind("<Leave>",lambda e,l=lab: l.configure(bg=SIDEBAR))
        ent.bind("<KeyRelease>",do_search); do_search()
    def open_file(path):
        try:
            with open(path,encoding="utf-8") as f: s=f.read()
            load_text(s,path)
        except Exception as e:
            messagebox.showerror("打开失败",str(e))
    def refresh_explorer():
        for w in file_list.winfo_children(): w.destroy()
        folder=os.path.basename(project_dir.rstrip("/\\")) if project_dir else "项目"
        root_row=tk.Frame(file_list,bg=SIDEBAR); root_row.pack(fill="x")
        tk.Label(root_row,text="▾ 📁 "+folder,bg=SIDEBAR,fg="#cccccc",font=("Microsoft YaHei UI",9,"bold"),anchor="w",padx=8,pady=3).pack(fill="x")
        try: files=sorted([f for f in os.listdir(project_dir) if f.endswith(".hxg")])
        except Exception: files=[]
        for f in files:
            full=os.path.join(project_dir,f)
            active = bool(cur["path"]) and os.path.abspath(cur["path"])==os.path.abspath(full)
            row=tk.Frame(file_list,bg="#37373d" if active else SIDEBAR); row.pack(fill="x")
            lab=tk.Label(row,text="  📄 "+f,bg="#37373d" if active else SIDEBAR,fg="#ffffff" if active else FG,font=UI_FONT,anchor="w",padx=14,pady=2,cursor="hand2")
            lab.pack(fill="x")
            lab.bind("<Button-1>",lambda e,p=full: open_file(p))
            lab.bind("<Enter>",lambda e,l=lab,ac=active: None if ac else l.configure(bg="#2a2d2e"))
            lab.bind("<Leave>",lambda e,l=lab,ac=active: None if ac else l.configure(bg=SIDEBAR))

    tabbar=tk.Frame(main,bg=TAB_BG,height=35)
    tabbar.pack(fill="x"); tabbar.pack_propagate(False)
    file_tab=tk.Frame(tabbar,bg=TAB_ACTIVE,height=35); file_tab.pack(side="left")
    tk.Label(file_tab,text="📄",bg=TAB_ACTIVE,fg="#4ec9b0",font=("Segoe UI Emoji",10),padx=10).pack(side="left",fill="y")
    tab_name=tk.Label(file_tab,text="未命名.hxg",bg=TAB_ACTIVE,fg="#ffffff",font=UI_FONT,padx=4)
    tab_name.pack(side="left",fill="y")
    tab_close=tk.Label(file_tab,text="×",bg=TAB_ACTIVE,fg="#858585",font=("Segoe UI",12),padx=10,cursor="hand2")
    tab_close.pack(side="left",fill="y")
    tk.Frame(main,bg=BORDER,height=1).pack(fill="x")

    crumb=tk.Frame(main,bg=BG,height=26); crumb.pack(fill="x"); crumb.pack_propagate(False)
    crumb_lbl=tk.Label(crumb,text="",bg=BG,fg=FG_DIM,font=("Microsoft YaHei UI",8),anchor="w",padx=14)
    crumb_lbl.pack(fill="both",expand=True)

    def refresh_tab():
        name=os.path.basename(cur["path"]) if cur["path"] else "未命名.hxg"
        tab_name.configure(text=name)
        root.title(name+" - HX Studio")
        if cur["path"]:
            parts=cur["path"].replace("\\","/").split("/")
            tail=parts[-2:] if len(parts)>=2 else parts
            crumb_lbl.configure(text="  ›  ".join(tail))
        else:
            crumb_lbl.configure(text="未命名.hxg")
        refresh_explorer()

    editor_wrap=tk.Frame(main,bg=BG)
    editor_wrap.pack(fill="both",expand=True)
    gutter=tk.Canvas(editor_wrap,width=58,bg=GUTTER_BG,highlightthickness=0,bd=0)
    gutter.pack(side="left",fill="y")
    ed=tk.Text(editor_wrap,font=LN_FONT,undo=True,wrap="none",bg=BG,fg=FG,insertbackground="#aeafad",selectbackground="#264f78",selectforeground="#ffffff",relief="flat",bd=0,padx=12,pady=8,highlightthickness=0,insertwidth=2,width=1)
    ed.pack(side="left",fill="both",expand=True)
    sb=tk.Scrollbar(editor_wrap,orient="vertical",bg="#424242",activebackground="#4f4f4f",troughcolor=BG,relief="flat",bd=0,width=14)
    sb.pack(side="right",fill="y")
    sb.configure(command=lambda *a: (ed.yview(*a), hooks["sync"]()))

    ed.tag_configure("kw",foreground="#569cd6")
    ed.tag_configure("str",foreground="#ce9178")
    ed.tag_configure("num",foreground="#b5cea8")
    ed.tag_configure("cmt",foreground="#6a9955")
    ed.tag_configure("bi",foreground="#dcdcaa")
    ed.tag_configure("cur",background="#2a3f5f")
    ed.tag_configure("err",background="#3a1d1d")

    wave_canvases=[]
    def clear_waves():
        for c in wave_canvases:
            try: c.destroy()
            except Exception: pass
        wave_canvases.clear()
    def forward_click(ev):
        if err["line"]:
            try:
                ed.mark_set("insert","%d.%d"%(err["line"],max(err["col"],0)))
                ed.see("insert"); ed.focus_set()
            except Exception: pass
    def draw_waves():
        clear_waves()
        if not err["line"]: return
        line=err["line"]
        b1=ed.bbox("%d.%d"%(line,max(err["col"],0)))
        if not b1: b1=ed.bbox("%d.0"%line)
        if not b1: return
        b2=ed.bbox("%d.end"%line)
        x1,y1,w1,h1=b1
        x2=b2[0] if b2 else x1+max(w1*8,140)
        if x2<=x1: x2=x1+max(w1,20)
        ww=max(x2-x1,10)
        c=tk.Canvas(ed,width=ww,height=6,bg=BG,highlightthickness=0,bd=0)
        pts=[]; x=1
        while x<=ww-1:
            pts.extend([x,3+1.4*math.sin(x*1.5)]); x+=3
        c.create_line(pts,fill=ERR_RED,width=1.6,smooth=True)
        c.place(x=x1,y=y1+h1-5)
        c.bind("<Button-1>",forward_click)
        c.bind("<MouseWheel>",lambda e:(ed.event_generate("<MouseWheel>",delta=e.delta),None))
        wave_canvases.append(c)
    def draw_gutter():
        gutter.delete("all")
        i=ed.index("@0,0")
        while True:
            info=ed.dlineinfo(i)
            if info is None: break
            y=info[1]; ln=i.split(".")[0]; n=int(ln)
            if n==err["line"]:
                gutter.create_rectangle(0,y-1,58,y+info[3]+1,fill="#3a1d1d",outline="")
                fg=ERR_RED
            else:
                fg=GUTTER_FG
            gutter.create_text(50,y+info[3]//2,anchor="e",text=ln,fill=fg,font=(LN_FONT[0],LN_FONT[1]-1))
            nxt=ed.index("%s+1line"%i)
            if nxt==i: break
            i=nxt

    tk.Frame(main,bg=BORDER,height=1).pack(fill="x")
    panel=tk.Frame(main,bg=PANEL,height=220)
    panel.pack(fill="x"); panel.pack_propagate(False)
    panel_tabs=tk.Frame(panel,bg=PANEL_HEAD,height=32)
    panel_tabs.pack(fill="x"); panel_tabs.pack_propagate(False)
    panel_stack=tk.Frame(panel,bg=PANEL)
    panel_stack.pack(fill="both",expand=True)

    ptab_out=tk.Label(panel_tabs,text="输出",bg=PANEL_HEAD,fg=FG_DIM,font=UI_FONT,padx=14,pady=6,cursor="hand2")
    ptab_out.pack(side="left")
    ptab_var=tk.Label(panel_tabs,text="变量",bg=PANEL_HEAD,fg=FG_DIM,font=UI_FONT,padx=14,pady=6,cursor="hand2")
    ptab_var.pack(side="left")
    ptab_prob=tk.Label(panel_tabs,text="问题",bg=PANEL_HEAD,fg=FG_DIM,font=UI_FONT,padx=14,pady=6,cursor="hand2")
    ptab_prob.pack(side="left")
    ptab_inp=tk.Label(panel_tabs,text="输入",bg=PANEL_HEAD,fg=FG_DIM,font=UI_FONT,padx=14,pady=6,cursor="hand2")
    ptab_inp.pack(side="left")

    out=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="word",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    var=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="none",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    prob=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="word",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    prob.tag_configure("err",foreground=ERR_RED)

    inp_panel=tk.Frame(panel_stack,bg=PANEL)
    inp_log=tk.Text(inp_panel,font=("Consolas",10),state="disabled",wrap="word",bg=PANEL,fg="#a0a0a0",relief="flat",bd=0,padx=14,pady=6,highlightthickness=0,height=3)
    inp_log.pack(fill="both",expand=True)
    inp_log.tag_configure("prompt",foreground="#9cdcfe")
    inp_log.tag_configure("value",foreground="#b5cea8")
    inp_row=tk.Frame(inp_panel,bg=PANEL)
    inp_row.pack(fill="x",padx=14,pady=(0,8))
    inp_entry=tk.Entry(inp_row,font=("Consolas",11),bg="#3c3c3c",fg=FG,insertbackground=FG,relief="flat",bd=0,highlightthickness=0)
    inp_entry.pack(side="left",fill="x",expand=True,ipady=6)
    inp_send=tk.Button(inp_row,text="发送",command=lambda: gui_input_submit(),bg=ACCENT,fg="#ffffff",activebackground=ACCENT_HOVER,activeforeground="#ffffff",relief="flat",bd=0,padx=14,pady=4,cursor="hand2",font=UI_FONT,highlightthickness=0,width=6)
    inp_send.pack(side="left",padx=(8,0))

    input_queue=queue.Queue()
    input_result={"waiting":False}

    def inp_log_append(text,tag=None):
        inp_log.configure(state="normal")
        if tag: inp_log.insert("end",text,tag)
        else: inp_log.insert("end",text)
        inp_log.see("end"); inp_log.configure(state="disabled")

    def gui_input_submit():
        val=inp_entry.get()
        inp_entry.delete(0,"end")
        inp_log_append(val+"\n","value")
        if input_result["waiting"]:
            input_queue.put(val)

    def gui_input_done():
        inp_send.configure(state="disabled",bg="#3a3a3d")
        ptab_inp.configure(fg=FG_DIM)

    def gui_input_begin():
        inp_send.configure(state="normal",bg=ACCENT)
        ptab_inp.configure(fg="#ffffff")
        inp_entry.focus_set()

    inp_entry.bind("<Return>",lambda e:(gui_input_submit(),"break")[1])

    panel_tab_state={"active":"out"}
    def switch_panel(which):
        panel_tab_state["active"]=which
        out.pack_forget(); var.pack_forget(); prob.pack_forget(); inp_panel.pack_forget()
        for lbl,w in [(ptab_out,"out"),(ptab_var,"var"),(ptab_prob,"prob"),(ptab_inp,"inp")]:
            if w==which: lbl.configure(fg="#ffffff",bg=PANEL)
            else: lbl.configure(fg=FG_DIM,bg=PANEL_HEAD)
        {"out":out,"var":var,"prob":prob,"inp":inp_panel}[which].pack(fill="both",expand=True)
    ptab_out.bind("<Button-1>",lambda e: switch_panel("out"))
    ptab_var.bind("<Button-1>",lambda e: switch_panel("var"))
    ptab_prob.bind("<Button-1>",lambda e: switch_panel("prob"))
    ptab_inp.bind("<Button-1>",lambda e: switch_panel("inp"))
    switch_panel("out")

    tk.Frame(root,bg=BORDER,height=1).pack(fill="x")
    status=tk.Frame(root,bg=STATUS_BG,height=24)
    status.pack(fill="x"); status.pack_propagate(False)
    tk.Label(status,text="⑂ main",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10).pack(side="left",fill="y")
    st_err=tk.Label(status,text="✕ 0  ⚠ 0",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10)
    st_err.pack(side="left",fill="y")
    st_msg=tk.Label(status,text="",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10,anchor="w")
    st_msg.pack(side="left",fill="x",expand=True)
    st_run=tk.Label(status,text="",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10)
    st_run.pack(side="right",fill="y")
    tk.Label(status,text="HX",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10).pack(side="right",fill="y")
    tk.Label(status,text="UTF-8",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10).pack(side="right",fill="y")
    st_pos=tk.Label(status,text="行 1, 列 1",bg=STATUS_BG,fg=STATUS_FG,font=UI_FONT,padx=10)
    st_pos.pack(side="right",fill="y")

    def update_status(msg=None):
        try:
            ln,col=ed.index("insert").split(".")
            st_pos.configure(text="行 %s, 列 %d"%(ln,int(col)+1))
        except Exception: pass
        if msg is not None: st_msg.configure(text=msg)
    def set_state(text,color=STATUS_FG): st_run.configure(text=text,fg=color)
    def update_err_badge(): st_err.configure(text="✕ 1  ⚠ 0" if err["line"] else "✕ 0  ⚠ 0")

    def sync_editor(): draw_gutter(); draw_waves(); update_status()
    def show_out(s):
        out.configure(state="normal"); out.delete("1.0","end")
        out.insert("1.0",s); out.see("end"); out.configure(state="disabled")
        if panel_tab_state["active"]!="out": switch_panel("out")
    def show_vars(d):
        var.configure(state="normal"); var.delete("1.0","end")
        var.insert("1.0","\n".join("%s = %s"%(k,v) for k,v in d.items()))
        var.configure(state="disabled")
    def show_problems(msg):
        prob.configure(state="normal"); prob.delete("1.0","end")
        if msg: prob.insert("1.0",msg,"err")
        prob.configure(state="disabled")
        if msg: switch_panel("prob")

    def mark_error(msg):
        ed.tag_remove("err","1.0","end")
        err["line"]=0; err["col"]=0
        m=re.search(r"第 (\d+) 行(?:第 (\d+) 列)?", msg)
        if m:
            ln=int(m.group(1)); col=int(m.group(2))-1 if m.group(2) else 0
            if col<0: col=0
            err["line"]=ln; err["col"]=col
            ed.tag_add("err","%d.0"%ln,"%d.end"%ln)
            try:
                ed.see("%d.0"%ln); ed.mark_set("insert","%d.%d"%(ln,col))
            except Exception: pass
            sync_editor()
        show_problems(msg.strip()); update_err_badge(); update_status(msg.strip())
        return msg
    def clear_error():
        ed.tag_remove("err","1.0","end")
        err["line"]=0; err["col"]=0
        show_problems(""); update_err_badge(); sync_editor()
    def highlight_line(line):
        ed.tag_remove("cur","1.0","end")
        if line:
            ed.tag_add("cur","%d.0"%line,"%d.end"%line)
            ed.see("%d.0"%line)
        sync_editor()

    def do_run():
        src=ed.get("1.0","end")
        if st["it"] is not None:
            try: st["it"].close_gwin()
            except Exception: pass
        it=Interp(root); st["it"]=it; st["trace"]=[]; st["i"]=-1
        def gui_ask():
            switch_panel("inp")
            input_result["waiting"]=True
            gui_input_begin()
            while True:
                try:
                    val=input_queue.get_nowait()
                    input_result["waiting"]=False
                    return val
                except queue.Empty:
                    pass
                root.update()
                time.sleep(0.02)
        it.ask_fn=gui_ask
        inp_log.configure(state="normal"); inp_log.delete("1.0","end"); inp_log.configure(state="disabled")
        input_result["waiting"]=False
        try:
            while True: input_queue.get_nowait()
        except queue.Empty: pass
        highlight_line(0); clear_error(); set_state("运行中…")
        try: prog=Parser(tokenize(src)).program()
        except SyntaxError as e:
            set_state("语法错误",ERR_RED); show_out(mark_error(str(e))+"\n"); return
        try: it.run(prog)
        except MiniError as e:
            st["trace"]=it.trace; set_state("运行错误",ERR_RED)
            show_out(it.text()+mark_error(str(e))+"\n"); return
        st["trace"]=it.trace
        show_out(it.text())
        show_vars(dict((k,fmt(v)) for k,v in it.globals.vars.items()))
        set_state("完成"); update_status("运行完成")
    def goto(i):
        line,vars_,olen=st["trace"][i]
        show_out("".join(st["it"].outbuf[:olen])); show_vars(vars_); highlight_line(line)
    def do_step():
        if not st["trace"]: do_run(); return
        i=st["i"]+1
        if i>=len(st["trace"]): return
        st["i"]=i; goto(i); set_state("单步 %d/%d"%(i+1,len(st["trace"])))
    def do_prev():
        if not st["trace"] or st["i"]<=0: return
        st["i"]-=1; goto(st["i"]); set_state("单步 %d/%d"%(st["i"]+1,len(st["trace"])))
    def do_clear():
        ed.delete("1.0","end"); show_out(""); show_vars({}); clear_error()
        set_state(""); update_status("就绪")
    def load_text(s,path=None):
        ed.delete("1.0","end"); ed.insert("1.0",s); hl(ed)
        clear_error(); cur["path"]=path; refresh_tab(); sync_editor()
    def do_new():
        ed.delete("1.0","end"); cur["path"]=None; clear_error()
        show_out(""); show_vars({}); refresh_tab(); sync_editor(); update_status("新建文件")
    def do_sample(): load_text(SAMPLE)
    def do_open():
        p=filedialog.askopenfilename(filetypes=[("HX 源码","*.hxg"),("所有文件","*.*")])
        if not p: return
        open_file(p)
    def do_save():
        p=cur["path"]
        if not p:
            p=filedialog.asksaveasfilename(defaultextension=".hxg",filetypes=[("HX 源码","*.hxg")])
            if not p: return
        with open(p,"w",encoding="utf-8") as f: f.write(ed.get("1.0","end-1c"))
        cur["path"]=p; refresh_tab(); update_status("已保存 %s"%os.path.basename(p))
    def do_save_as():
        p=filedialog.asksaveasfilename(defaultextension=".hxg",filetypes=[("HX 源码","*.hxg")])
        if not p: return
        with open(p,"w",encoding="utf-8") as f: f.write(ed.get("1.0","end-1c"))
        cur["path"]=p; refresh_tab(); update_status("已保存 %s"%os.path.basename(p))
    def load_ui_from_editor():
        code = ed.get("1.0", "end-1c")
        parsed = ui_parse_code(code)
        if not parsed:
            messagebox.showinfo("提示", "当前编辑器里没有找到 ui* 组件代码。\n\n支持的：uiwin / uibtn / uilabel / uiinput / uitext / uicheck / uilist / uirange / uiprogress")
            return
        open_ui_designer(root, ed, hl, sync_editor, initial_items=parsed)
        update_status("已加载 %d 个组件到设计器" % len(parsed))

    def do_cheat():
        win=tk.Toplevel(root); win.title("HX 语法速查"); win.geometry("760x720")
        win.configure(bg=BG)
        txt=tk.Text(win,font=("Consolas",11),wrap="word",bg=BG,fg=FG,relief="flat",bd=0,padx=14,pady=10,highlightthickness=0)
        txt.pack(fill="both",expand=True)
        txt.insert("1.0",cheatsheet_text())
        txt.tag_configure("sec",font=("Microsoft YaHei",11,"bold"),foreground="#569cd6")
        txt.tag_configure("item",foreground="#d4d4d4")
        for i,line in enumerate(cheatsheet_text().split("\n"),1):
            if line.startswith("【"): txt.tag_add("sec","%d.0"%i,"%d.end"%i)
            elif line.strip(): txt.tag_add("item","%d.0"%i,"%d.end"%i)
        txt.configure(state="disabled")

    def close_tab():
        ed.delete("1.0","end"); cur["path"]=None
        refresh_tab(); clear_error(); show_out(""); show_vars({})
    tab_close.bind("<Button-1>",lambda e: close_tab())
    tab_close.bind("<Enter>",lambda e: tab_close.configure(fg="#ffffff",bg="#3a3a3d"))
    tab_close.bind("<Leave>",lambda e: tab_close.configure(fg="#858585",bg=TAB_ACTIVE))

    ai_cfg=ai_load_config()
    ai_state={"busy":False,"history":[]}
    ai_q=queue.Queue()

    ai_head=tk.Frame(ai_panel,bg=PANEL_HEAD,height=35)
    ai_head.pack(fill="x"); ai_head.pack_propagate(False)
    tk.Label(ai_head,text="🤖 小智",bg=PANEL_HEAD,fg="#9cdcfe",font=("Microsoft YaHei UI",10,"bold"),padx=12).pack(side="left",fill="y")
    tk.Label(ai_head,text="HX 向导",bg=PANEL_HEAD,fg=FG_DIM,font=UI_FONT,padx=4).pack(side="left",fill="y")
    ai_set_btn=tk.Label(ai_head,text="⚙",bg=PANEL_HEAD,fg=FG_DIM,font=("Microsoft YaHei UI",12),cursor="hand2",padx=10)
    ai_set_btn.pack(side="right",fill="y")

    ai_bottom=tk.Frame(ai_panel,bg=PANEL_HEAD,height=160)
    ai_bottom.pack(side="bottom",fill="x"); ai_bottom.pack_propagate(False)
    chat_frame=tk.Frame(ai_panel,bg=BG)
    chat_frame.pack(fill="both",expand=True)
    chat=tk.Text(chat_frame,height=1,width=1,font=("Microsoft YaHei UI",9),wrap="word",bg=BG,fg=FG,relief="flat",bd=0,padx=10,pady=8,highlightthickness=0,state="disabled",cursor="arrow",spacing1=2,spacing3=6)
    chat_sb=tk.Scrollbar(chat_frame,orient="vertical",bg="#424242",troughcolor=BG,relief="flat",bd=0,width=10,command=chat.yview)
    chat_sb.pack(side="right",fill="y")
    chat.pack(side="left",fill="both",expand=True)
    chat.configure(yscrollcommand=chat_sb.set)
    chat.tag_configure("user_label",foreground="#569cd6",font=("Microsoft YaHei UI",9,"bold"))
    chat.tag_configure("user_text",foreground="#c8c8c8",lmargin1=6,lmargin2=6)
    chat.tag_configure("ai_label",foreground="#dcdcaa",font=("Microsoft YaHei UI",9,"bold"))
    chat.tag_configure("ai_text",foreground="#d4d4d4",lmargin1=6,lmargin2=6)
    chat.tag_configure("sys",foreground="#6a9955",font=("Microsoft YaHei UI",8))
    chat.tag_configure("insert_btn",foreground="#4ec9b0",font=("Microsoft YaHei UI",9,"underline"),lmargin1=6,lmargin2=6)
    chat.tag_configure("design_btn",foreground="#dcdcaa",font=("Microsoft YaHei UI",9,"underline"),lmargin1=6,lmargin2=6)
    chat.tag_configure("code",foreground="#ce9178",background="#1b1b1b",font=("Consolas",9),lmargin1=10,lmargin2=10,spacing1=3,spacing3=3)
    chat.tag_configure("err",foreground="#f14c4c")

    ai_opts=tk.Frame(ai_bottom,bg=PANEL_HEAD); ai_opts.pack(fill="x",padx=10,pady=(6,0))
    attach_var=tk.BooleanVar(value=True)
    tk.Checkbutton(ai_opts,text="附带当前代码",variable=attach_var,bg=PANEL_HEAD,fg=FG_DIM,selectcolor="#3a3a3d",activebackground=PANEL_HEAD,activeforeground=FG,font=UI_FONT,bd=0,highlightthickness=0).pack(side="left")
    input_row=tk.Frame(ai_bottom,bg=PANEL_HEAD); input_row.pack(fill="x",padx=10,pady=(4,10))
    ai_input=tk.Text(input_row,height=3,width=1,font=("Microsoft YaHei UI",9),wrap="word",bg="#3c3c3c",fg=FG,insertbackground="#aeafad",relief="flat",bd=0,padx=8,pady=6,highlightthickness=0)
    ai_input.pack(side="left",fill="both",expand=True)

    def ai_send_btn_state(busy):
        if busy: ai_send.configure(state="disabled",bg="#3a3a3d",text="…")
        else: ai_send.configure(state="normal",bg=ACCENT,text="发送")
    ai_send=tk.Button(input_row,text="发送",command=lambda: ai_send_msg(),bg=ACCENT,fg="#ffffff",activebackground=ACCENT_HOVER,activeforeground="#ffffff",relief="flat",bd=0,padx=14,pady=8,cursor="hand2",font=UI_FONT,highlightthickness=0,width=6)
    ai_send.pack(side="right",fill="y",padx=(8,0))

    def chat_append(text,tag="ai_text"):
        chat.configure(state="normal"); chat.insert("end",text,tag)
        chat.see("end"); chat.configure(state="disabled")
    def chat_clear():
        chat.configure(state="normal"); chat.delete("1.0","end"); chat.configure(state="disabled")
    def ai_welcome():
        chat_clear()
        if not ai_cfg.get("base_url"):
            chat_append("你好，我是小智 🤖\n\n", "ai_label")
            chat_append("我还没配置 API。点击右上角 ⚙ 填一下：\n"
                        "  • Base URL  例如 https://api.deepseek.com/v1\n"
                        "  • API Key   你的密钥\n"
                        "  • Model     例如 deepseek-chat\n\n"
                        "配好后我就能帮你在 HX 语言里闯荡啦。\n", "sys")
        else:
            chat_append("你好，我是小智 🤖\n", "ai_label")
            chat_append("我是你的 HX 语言向导，可以帮你写代码、查错、讲解语法。\n"
                        "直接输入问题，回车发送（Shift+Enter 换行）。\n", "ai_text")

    def ai_config_dialog():
        win=tk.Toplevel(root); win.title("小智 · API 配置")
        win.geometry("480x300"); win.configure(bg=BG)
        win.transient(root); win.grab_set()
        tk.Label(win,text="OpenAI 兼容接口配置",bg=BG,fg="#9cdcfe",font=("Microsoft YaHei UI",11,"bold")).pack(anchor="w",padx=18,pady=(16,10))
        rows=[("Base URL","base_url"),("API Key","api_key"),("Model","model")]
        ents={}
        for label,key in rows:
            tk.Label(win,text=label,bg=BG,fg=FG_DIM,font=UI_FONT).pack(anchor="w",padx=18)
            e=tk.Entry(win,font=("Consolas",10),bg="#3c3c3c",fg=FG,insertbackground=FG,relief="flat",bd=0,highlightthickness=1,highlightbackground=BORDER2,highlightcolor=ACCENT)
            e.insert(0,ai_cfg.get(key,"")); e.pack(fill="x",padx=18,pady=(2,8))
            ents[key]=e
        tk.Label(win,text="支持 DeepSeek / Kimi / 通义 / 智谱 / Ollama 等 OpenAI 兼容服务",bg=BG,fg="#6a737d",font=("Microsoft YaHei UI",8)).pack(anchor="w",padx=18)
        def save():
            for k,e in ents.items(): ai_cfg[k]=e.get().strip()
            ok=ai_save_config(ai_cfg); win.destroy()
            if ok: update_status("小智配置已保存"); ai_welcome()
            else: update_status("配置保存失败")
        bf=tk.Frame(win,bg=BG); bf.pack(fill="x",padx=18,pady=14)
        tk.Button(bf,text="保存",command=save,bg=ACCENT,fg="#ffffff",activebackground=ACCENT_HOVER,relief="flat",bd=0,padx=18,pady=6,cursor="hand2",font=UI_FONT).pack(side="right")
        tk.Button(bf,text="取消",command=win.destroy,bg="#3a3a3d",fg=FG,activebackground="#4a4a4d",relief="flat",bd=0,padx=14,pady=6,cursor="hand2",font=UI_FONT).pack(side="right",padx=(0,8))
    ai_set_btn.bind("<Button-1>",lambda e: ai_config_dialog())

    def ai_render_reply(content):
        parts=content.split(FENCE); i=0
        for part in parts:
            if i % 2 == 1:
                body=part; nl=body.find("\n")
                if nl >= 0: body=body[nl+1:]
                chat_append(body.rstrip()+"\n", "code")
                chat.configure(state="normal")
                chat.insert("end","📋 双击此处插入代码\n\n",("insert_btn",))
                if "uiwin(" in body or "uibtn(" in body or "uilabel(" in body:
                    chat.insert("end","🧩 双击此处载入设计器\n\n",("design_btn",))
                chat.configure(state="disabled")
            else:
                if part: chat_append(part, "ai_text")
            i+=1
    def ai_send_msg():
        if ai_state["busy"]: return
        text=ai_input.get("1.0","end-1c").strip()
        if not text: return
        if not ai_cfg.get("base_url"): ai_config_dialog(); return
        ai_input.delete("1.0","end")
        chat_append("你：\n", "user_label"); chat_append(text+"\n\n", "user_text")
        msg=text
        if attach_var.get():
            code=ed.get("1.0","end-1c").strip()
            if code: msg=("当前编辑器代码：\n"+FENCE+"hxg\n"+code+"\n"+FENCE+"\n\n用户问题："+text)
        ai_state["history"].append({"role":"user","content":msg})
        ai_state["busy"]=True; ai_send_btn_state(True)
        chat_append("小智正在思考…\n", "sys")
        cfg=dict(ai_cfg); hist=list(ai_state["history"])
        ai_state["streaming"]=True
        def worker():
            try:
                def on_chunk(p):
                    ai_q.put(("chunk", p))
                full=ai_chat_stream(cfg, hist, on_chunk)
                ai_q.put(("ok", full))
            except Exception as e:
                ai_q.put(("err", str(e)))
        threading.Thread(target=worker, daemon=True).start()
    def ai_poll():
        try:
            while True:
                kind,val=ai_q.get_nowait()
                chat.configure(state="normal")
                # 首次收到数据：删掉"正在思考"，插入"小智："标题，记录流式起点
                if ai_state.get("streaming"):
                    idx=chat.search("小智正在思考…","1.0","end")
                    if idx:
                        end=chat.index(idx+" lineend +1c"); chat.delete(idx,end)
                    chat.insert("end","小智：\n","ai_label")
                    ai_state["stream_start"]=chat.index("end-1c")
                    ai_state["streaming"]=False
                if kind=="chunk":
                    chat.insert("end", val, "ai_text")
                    chat.see("end")
                elif kind=="ok":
                    # 删除流式原文，用格式化渲染替换
                    start=ai_state.get("stream_start")
                    if start:
                        chat.delete(start, "end")
                    chat.insert("end","小智：\n","ai_label")
                    chat.configure(state="disabled")
                    ai_state["history"].append({"role":"assistant","content":val})
                    ai_render_reply(val)
                    chat.configure(state="normal")
                    ai_state["stream_start"]=None
                    ai_state["busy"]=False; ai_send_btn_state(False)
                elif kind=="err":
                    start=ai_state.get("stream_start")
                    if start:
                        chat.delete(start, "end")
                    chat.insert("end","出错了："+val+"\n\n","err")
                    chat.see("end")
                    ai_state["stream_start"]=None
                    ai_state["busy"]=False; ai_send_btn_state(False)
                chat.configure(state="disabled")
        except queue.Empty: pass
        root.after(60, ai_poll)
    def ai_key(ev):
        if ev.state & 0x0001 and ev.keysym=="Return": return None
        if ev.keysym=="Return" and not (ev.state & 0x0001):
            ai_send_msg(); return "break"
    ai_input.bind("<Return>", ai_key)
    ai_input.bind("<Shift-Return>", lambda e: None)
    def _code_before(pos):
        code_ranges=chat.tag_ranges("code"); code_text=""
        for j in range(0,len(code_ranges),2):
            cs,ce=code_ranges[j],code_ranges[j+1]
            if chat.compare(ce,"<=",pos): code_text=chat.get(cs,ce)
        return code_text

    def chat_click(ev):
        idx=chat.index("@%d,%d"%(ev.x,ev.y))
        # 插入到编辑器
        ranges=chat.tag_ranges("insert_btn")
        for i in range(0,len(ranges),2):
            s,en=ranges[i],ranges[i+1]
            if chat.compare(s,"<=",idx) and chat.compare(idx,"<=",en):
                code_text=_code_before(s)
                if code_text:
                    ed.insert("insert",code_text)
                    hl(ed); sync_editor(); ed.focus_set()
                    update_status("已插入代码到编辑器")
                return
        # 载入设计器
        ranges=chat.tag_ranges("design_btn")
        for i in range(0,len(ranges),2):
            s,en=ranges[i],ranges[i+1]
            if chat.compare(s,"<=",idx) and chat.compare(idx,"<=",en):
                code_text=_code_before(s)
                if code_text:
                    parsed=ui_parse_code(code_text)
                    if parsed:
                        open_ui_designer(root,ed,hl,sync_editor,initial_items=parsed)
                        update_status("已载入 %d 个组件到设计器" % len(parsed))
                    else:
                        messagebox.showinfo("提示","这段代码里没有可识别的 UI 组件")
                return
    chat.bind("<Double-Button-1>",chat_click)
    chat.bind("<Key>",lambda e:"break")

    ai_welcome(); ai_poll()

    ed.configure(yscrollcommand=lambda a,b: (sb.set(a,b), hooks["sync"]()))
    hooks["sync"]=sync_editor
    ed.bind("<KeyRelease>",lambda e: (hl(ed), sync_editor()))
    ed.bind("<ButtonRelease-1>",lambda e: update_status())
    ed.bind("<MouseWheel>",lambda e: root.after(1, sync_editor))
    ed.bind("<Configure>",lambda e: root.after(1, sync_editor))
    root.bind("<F5>",lambda e: (do_run(),"break")[1])
    root.bind("<F10>",lambda e: (do_step(),"break")[1])
    root.bind("<Control-o>",lambda e: (do_open(),"break")[1])
    root.bind("<Control-s>",lambda e: (do_save(),"break")[1])
    root.bind("<Control-n>",lambda e: (do_new(),"break")[1])
    root.bind("<Control-b>",lambda e: (toggle_sidebar(),"break")[1])
    root.bind("<Control-u>",lambda e: (open_ui_designer(root,ed,hl,sync_editor),"break")[1])

    if initial_path and os.path.exists(initial_path):
        with open(initial_path,encoding="utf-8") as f: s=f.read()
        load_text(s,initial_path)
    else:
        ed.insert("1.0",SAMPLE); hl(ed)
        refresh_tab()

    set_activity("files")
    ed.focus_set()
    sync_editor()
    root.mainloop()


if __name__=="__main__":
    args=sys.argv[1:]
    edit_path=None
    if "--edit" in args:
        i=args.index("--edit")
        rest=args[i+1:]
        if rest: edit_path=rest[0]
        args=args[:i]+rest[1:]
    if edit_path:
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
        build_gui(edit_path)
    elif args:
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
    else:
        build_gui()
