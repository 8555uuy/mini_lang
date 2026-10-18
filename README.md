# HX 语言

一个用 Python 实现的迷你脚本语言解释器，单文件 `hx.py`，零依赖（图形界面需要 tkinter / PyQt5）。

## 特性

- **自动类型推断**：直接写 `x = 10;`，无需声明类型
- **C 风格函数**：`add(a, b) { return a + b; }`
- **带括号的控制流**：`if (...) { }` / `while (...) { }` / `for (...; ...; ...) { }`
- **异常处理**：`try { } catch (e) { }`
- **数据结构**：数组、字典、函数（支持递归）
- **丰富内置函数**：字符串、数学、数组、字典操作
- **格式输入**：`scanf("%d %d", a, b)`
- **图形绘制**：`gwin` / `gline` / `grect` / `gcircle` / `gtext`
- **鼠标键盘事件**：`gwaitkey` / `gwaitclick` / `gkeydown` / `gclick`
- **界面组件**：16 种 UI 控件（`uiwin` / `uibtn` / `uiinput` …），基于 PyQt5
- **文件与系统**：`readfile` / `writefile` / `openurl` / `runapp`
- **网络**：`http_get` / `http_download`，支持后台异步 `bg_run`
- **压缩与哈希**：`md5` / `sha256` / `unzip` / `zipinfo`

## 快速开始

```bash
python hx.py demo.hxg
```

## 语法速览

```hx
# 变量：直接赋值，自动判断类型
x = 10;
s = "hello";
arr = [1, 2, 3];
d = {name: "hx", ver: 3};

# 函数
fib(n) {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}

print("fib(10) =", fib(10));

# 条件
if (x > 5) {
  print("big");
} else if (x > 0) {
  print("small");
} else {
  print("zero or negative");
}

# 循环
for (i = 0; i < len(arr); i += 1) {
  print(arr[i]);
}

i = 0;
while (i < 3) {
  print("i =", i);
  i += 1;
}

# 逻辑运算（也支持 and / or / not）
if (x > 0 && x < 10) { print("个位数"); }
if (x < 0 || x > 100) { print("超出范围"); }

# 异常
try {
  print(undefined_var);
} catch (e) {
  print("error:", e);
}
```

程序内运行 `help()` 可随时查看完整语法速查。

## 内置函数

| 类别 | 函数 |
|---|---|
| 类型 | `type(x)` |
| 输出输入 | `print(...)` `input(prompt)` `scanf(fmt, vars...)` `help()` |
| 数组 | `len` `push` `min` `max` `abs` `range` |
| 字典 | `keys` `items` `has` `set` |
| 字符串 | `upper` `lower` `trim` `split` `join` |
| 转换 | `str` `num` |
| 数学 | `sqrt` `sin` `cos` `tan` `floor` `ceil` `round` `random` `PI` |
| 图形 | `gwin` `gline` `grect` `gcircle` `gtext` `gclear` `gsleep` |
| 事件 | `gwaitkey` `gwaitclick` `gkeydown` `gclick` |
| 文件系统 | `readfile` `writefile` `appendfile` `exists` `files` `openfile` `openurl` `runapp` |
| 网络 | `http_get` `http_download` |
| 后台 | `bg_run(fn, args..., callback)` |
| 压缩哈希 | `md5` `sha256` `unzip` `zipinfo` |

## 图形绘制

```hx
gwin(600, 400, "我的画板");
grect(0, 0, 600, 400, "white", "lightcyan");
gcircle(300, 200, 80, "orange", "gold");
gline(50, 350, 550, 350, "blue", 3);
gtext(250, 50, "Hello!", "navy");
gsleep(2000);
```

完整示例见 `graphics.hxg`。

## 事件处理

```hx
gwin(400, 300, "按键演示");

# 阻塞式：等待按键，超时返回空字符串
k = gwaitkey(3000);
if (k != "") { print("你按了:", k); }

# 阻塞式：等待点击，返回 [x, y]
p = gwaitclick(3000);
if (len(p) > 0) { print("点击位置:", p[0], p[1]); }

# 回调式：适合游戏/动画
on_key(key) { print("按键:", key); }
gkeydown(on_key);
```

完整示例见 `snake.hxg`（贪吃蛇小游戏）。

## 界面组件

16 种控件，统一签名 `(id, x, y, 宽, 高, ...)`：

| 组件 | 函数 |
|---|---|
| 标题 / 标签 / 按钮 | `uiheading` / `uilabel` / `uibtn` |
| 输入框 / 多行文本 | `uiinput` / `uitext` |
| 勾选框 / 单选组 / 下拉框 / 列表框 | `uicheck` / `uiradio` / `uicombo` / `uilist` |
| 滑块 / 进度条 | `uirange` / `uiprogress` |
| 图片 / 表格 | `uiimage` / `uitable` |
| 面板 / 分割线 / 标签页 | `uipanel` / `uiseparator` / `uitabs` |

事件用 `uion(id, "click", fn)` 绑定，`uiget` / `uiset` 读写值，`uirun()` 启动。

```hx
uiwin(400, 300, "登录");
uilabel("lb", 20, 20, 80, 26, "用户名：");
uiinput("inp", 100, 20, 260, 28);
uibtn("ok", 20, 70, 100, 32, "登录");
uilabel("res", 20, 120, 360, 26, "");

on_login() {
  if (uiget("inp") == "admin") {
    uiset("res", "登录成功");
  } else {
    uiset("res", "用户名错误");
  }
}
uion("ok", "click", on_login);
uirun();
```

## 后台任务

`bg_run` 在后台线程执行内置 IO 函数，完成后在主线程调用回调（回调里可以安全操作 UI）：

```hx
on_done(text) {
  uiset("status", "收到 " + len(text) + " 字节");
}
bg_run(http_get, "https://example.com", on_done);
uirun();
```

**限制**：`bg_run` 只接受内置 IO 函数（`http_get` / `readfile` / `md5` 等），不能传入用户自定义函数——后台线程无法安全访问解释器状态。

## 示例文件

| 文件 | 内容 |
|---|---|
| `demo.hxg` | 基础语法综合演示 |
| `t.hxg` | 数据结构操作 |
| `f4.hxg` | 异常处理 |
| `auto.hxg` | 内置函数 |
| `graphics.hxg` | 图形绘制 |
| `snake.hxg` | 贪吃蛇游戏（按键事件） |

## 项目结构

```
hx.py          解释器（词法、语法、求值、内置函数、图形、UI、网络）
*.hxg          示例程序
```
