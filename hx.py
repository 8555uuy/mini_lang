# MiniLang v2 —— 解释器 + Tkinter 编码器
# 语法：x = 1;  f(a,b){...}  if/else if/else  while  for  return
#       print("hi", 1);  数组 [1,2]  字典 {a:1}  字符串 "x" 或 'x'  注释 #
import sys, re, os, math, json, threading, queue, time
import urllib.request, urllib.error

KEYWORDS = {"let","dar","if","else","elif","while","for","in","break","continue","del",
            "return","true","false","null","and","or","not","try","catch"}
OPS = ["==","!=","<=",">=","+=","-=","*=","/=","%=","+","-","*","/","%","<",">","=",
       "(",")","{","}","[","]",",",";",":","."]

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
        if t.k=="let" or (t.k=="dar" and self.peek(1).k!="("):
            raise SyntaxError("第 %d 行：%s 声明已废弃，请直接写 x = 1;（自动判断类型）" % (line,t.k))
        if t.k=="id" and t.v=="print" and self.peek(1).k!="(":
            raise SyntaxError("第 %d 行：print 必须加括号，写成 print(...)" % line)
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
            self.take("(")
            if self.at("id") and self.peek(1).k=="in":
                name=self.take("id").v; self.take("in")
                seq=self.expr(); self.take(")")
                return ("forin",name,seq,self.stmt(),line)
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
        while self.eat("or"):
            node=("bin","or",node,self.and_(),node[-1])
        return node

    def and_(self):
        node=self.not_()
        while self.eat("and"):
            node=("bin","and",node,self.not_(),node[-1])
        return node

    def not_(self):
        if self.at("not"):
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
        if t.k=="dar" and self.peek(1).k!="(":
            raise SyntaxError("第 %d 行：dar 声明已废弃，请直接写 x = 1;（自动判断类型）" % t.line)
        if t.k=="id" or t.k=="dar":
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
        g=self.globals
        g.define("dar",Native(lambda a: typename(a[0])))
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

    def ask(self):
        if self.ask_fn: return self.ask_fn()
        try: return input()
        except Exception: return ""

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
            self.gcanvas = tk.Canvas(self.gwin,width=w,height=h,bg="white",highlightthickness=0)
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
        elif k=="forin":
            seq=self.ev(n[2])
            if isinstance(seq,dict): seq=list(seq.keys())
            if not isinstance(seq,(list,str,dict)):
                raise MiniError("第 %d 行：for x in ... 只能遍历数组/字符串/字典" % n[-1])
            for item in list(seq):
                self.env.define(n[1],item)
                try: self.ex(n[3])
                except BreakSig: break
                except ContinueSig: continue
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

    def ev(self,n):
        k=n[0]
        if k in ("num","str","bool","null"): return n[1]
        if k=="cat": return "".join(fmt(self.ev(p)) for p in n[1])
        if k=="id": return self.env.get(n[1])
        if k=="list": return [self.ev(x) for x in n[1]]
        if k=="dict": return dict((kk,self.ev(v)) for kk,v in n[1])
        if k=="un":
            v=self.ev(n[2])
            return (-v) if n[1]=="-" else (not truth(v))
        if k=="bin":
            op=n[1]
            if op=="and":
                l=self.ev(n[2])
                return self.ev(n[3]) if truth(l) else l
            if op=="or":
                l=self.ev(n[2])
                return l if truth(l) else self.ev(n[3])
            l=self.ev(n[2]); r=self.ev(n[3])
            if op=="==": return l==r
            if op=="!=": return l!=r
            if op=="+":
                if isinstance(l,str) or isinstance(r,str): return fmt(l)+fmt(r)
                return l+r
            if op=="-": return l-r
            if op=="*": return l*r
            if op=="/":
                if r==0: raise ZeroDivisionError()
                return l/r
            if op=="%":
                if r==0: raise ZeroDivisionError()
                return l%r
            if op=="<": return l<r
            if op==">": return l>r
            if op=="<=": return l<=r
            if op==">=": return l>=r
            raise MiniError("未知运算符 %s" % op)
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
  "dar(x)               查询类型：数字/字符串/布尔/数组/字典/函数/空",
  "true / false / null  布尔与空值字面量",
  "注意：let / dar 声明写法已移除，直接写 x = 1;",
],
"输出与输入": [
  'print("hi", 1);     输出，多参数用空格分隔',
  'print();             无参数输出一个空行',
  'input("提示")        读一行输入（命令行）',
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
  "for (x in arr) { ... }     遍历 数组/字符串/字典(键)",
  "for (i = 0; i < n; i += 1) { ... }   C 式三段循环，三段均可省略",
  "break;   continue;",
  "try { ... } catch (e) { ... }   捕获错误，e 为错误信息",
  "and / or / not",
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
"注释": ["# 这一行是注释"],
}

CHEAT_ORDER = ["变量","输出与输入","函数","控制流","运算符","数组","字典","字符串","图形","注释"]

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
print("dar(n) =", dar(n), "| n =", n);
s = "hi";
print("dar(s) =", dar(s));
arr2 = [1, 2];
print("dar(arr2) =", dar(arr2));
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

for (x in arr) { print("项:", x); }
for (j = 0; j < 3; j += 1) { print("j =", j); }

s = "hi";
print(s + "!" + 1);
if (sum > 5 and true) { print("ok"); } else { print("bad"); }
'''

TOKRE = re.compile(r'#[^\n]*|"[^"\n]*"|\'[^\'\n]*\'|\b\d+(?:\.\d+)?\b|\b(?:dar|if|elif|else|while|for|in|return|true|false|null|and|or|not|try|catch|break|continue|del)\b|\b(?:print|len|push|keys|str|num|range|input|help)\b')
KW = {"dar","if","else","elif","while","for","in","break","continue","del","return","true","false","null","and","or","not","try","catch"}


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
    "- 循环：while (c) { }  /  for (x in arr) { }  /  for (i = 0; i < n; i += 1) { }\n"
    "- 异常：try { } catch (e) { }\n"
    "- 字符串插值：\"hi \u0024{x}\"\n"
    "- print 必须加括号：print(\"hi\", 1);\n"
    "- 内置：dar(x) 查类型、len、push、min、max、abs、range、keys、items、has、set、upper、lower、trim、split、join、str、num、input、help\n"
    "- 图形：gwin(w,h,title) 建窗口、gline(x1,y1,x2,y2,color,width)、grect(x1,y1,x2,y2,color,fill)、"
    "gcircle(cx,cy,r,color,fill)、gtext(x,y,text,color)、gclear()、gsleep(ms) 刷新并暂停\n"
    "- 注释用 #，语句末尾分号可省\n\n"
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

    out=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="word",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    var=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="none",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    prob=tk.Text(panel_stack,font=("Consolas",11),state="disabled",wrap="word",bg=PANEL,fg=FG,insertbackground=FG,relief="flat",bd=0,padx=14,pady=8,highlightthickness=0)
    prob.tag_configure("err",foreground=ERR_RED)

    panel_tab_state={"active":"out"}
    def switch_panel(which):
        panel_tab_state["active"]=which
        out.pack_forget(); var.pack_forget(); prob.pack_forget()
        for lbl,w in [(ptab_out,"out"),(ptab_var,"var"),(ptab_prob,"prob")]:
            if w==which: lbl.configure(fg="#ffffff",bg=PANEL)
            else: lbl.configure(fg=FG_DIM,bg=PANEL_HEAD)
        {"out":out,"var":var,"prob":prob}[which].pack(fill="both",expand=True)
    ptab_out.bind("<Button-1>",lambda e: switch_panel("out"))
    ptab_var.bind("<Button-1>",lambda e: switch_panel("var"))
    ptab_prob.bind("<Button-1>",lambda e: switch_panel("prob"))
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
        it.ask_fn=lambda: (simpledialog.askstring("HX 输入","请输入：",parent=root) or "")
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
        def worker():
            try: ai_q.put(("ok", ai_chat(cfg, hist)))
            except Exception as e: ai_q.put(("err", str(e)))
        threading.Thread(target=worker, daemon=True).start()
    def ai_poll():
        try:
            while True:
                kind,val=ai_q.get_nowait()
                chat.configure(state="normal")
                idx=chat.search("小智正在思考…","1.0","end")
                if idx:
                    end=chat.index(idx+" lineend +1c"); chat.delete(idx,end)
                chat.configure(state="disabled")
                if kind=="ok":
                    ai_state["history"].append({"role":"assistant","content":val})
                    chat_append("小智：\n","ai_label"); ai_render_reply(val)
                else:
                    chat_append("出错了："+val+"\n\n","err")
                ai_state["busy"]=False; ai_send_btn_state(False)
        except queue.Empty: pass
        root.after(120, ai_poll)
    def ai_key(ev):
        if ev.state & 0x0001 and ev.keysym=="Return": return None
        if ev.keysym=="Return" and not (ev.state & 0x0001):
            ai_send_msg(); return "break"
    ai_input.bind("<Return>", ai_key)
    ai_input.bind("<Shift-Return>", lambda e: None)
    def chat_click(ev):
        idx=chat.index("@%d,%d"%(ev.x,ev.y))
        ranges=chat.tag_ranges("insert_btn")
        for i in range(0,len(ranges),2):
            s,en=ranges[i],ranges[i+1]
            if chat.compare(s,"<=",idx) and chat.compare(idx,"<=",en):
                code_ranges=chat.tag_ranges("code"); code_text=""
                for j in range(0,len(code_ranges),2):
                    cs,ce=code_ranges[j],code_ranges[j+1]
                    if chat.compare(ce,"<=",s): code_text=chat.get(cs,ce)
                if code_text:
                    ed.insert("insert",code_text)
                    hl(ed); sync_editor(); ed.focus_set()
                    update_status("已插入代码到编辑器")
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
