# MiniLang / HX 语言

一个用 Python 实现的迷你脚本语言解释器，附带 VS Code 风格的集成开发环境（HX Studio）。

## 特性

- **自动类型推断**：直接写 `x = 10;` 即可，无需声明类型
- **带括号的控制流**：`if (...)` / `else if (...)` / `while (...)` / `for (...)`
- **C 式 for 循环**：`for (i = 0; i < n; i += 1)`，三段均可省略
- **异常处理**：`try { ... } catch (e) { ... }`
- **字符串插值**：`"hi ${x}!"`
- **丰富数据结构**：数组、字典、函数、闭包
- **内置图形绘制**：`gwin` / `gline` / `grect` / `gcircle` / `gtext`，用代码画图
- **HX Studio 编辑器**：VS Code 风格界面（菜单栏 / 活动栏 / 资源管理器 / 标签页 / 面包屑 / 状态栏）
- **开发辅助**：语法高亮、行号、错误红色波浪线、单步调试、变量观察、问题面板

## 快速开始

```bash
# 命令行运行
python hx.py demo.hxg

# 打开 HX Studio
python hx.py

# 用 Studio 打开指定文件
python hx.py --edit demo.hxg
```

## 语法速览

```hx
# 变量：直接赋值，自动判断类型
x = 10;
s = "hello";
arr = [1, 2, 3];
d = {name: "hx", ver: 3};

# 函数（C 风格）
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

# while
i = 0;
while (i < 3) {
  print("i =", i);
  i += 1;
}

# 遍历字典的键
ks = keys(d);
for (i = 0; i < len(ks); i += 1) { print(ks[i]); }

# for - C 式三段
for (i = 0; i < len(arr); i += 1) {
  print(arr[i]);
}

# 异常
try {
  print(undefined_var);
} catch (e) {
  print("error:", e);
}

# 字符串插值
print("x = ${x}, x+1 = ${x + 1}");
```

程序内运行 `help()` 可随时查看完整语法速查。

## 内置函数

| 类别 | 函数 |
|---|---|
| 类型 | `dar(x)` 查询类型 |
| 输出 | `print(...)` `input(prompt)` `help()` |
| 数组 | `len` `push` `min` `max` `range` `abs` |
| 字典 | `keys` `items` `has` `set` |
| 字符串 | `upper` `lower` `trim` `split` `join` |
| 转换 | `str` `num` |
| 数学 | `sqrt` `sin` `cos` `tan` `floor` `ceil` `round` `random` `PI` |
| 图形 | `gwin` `gline` `grect` `gcircle` `gtext` `gclear` `gsleep` |

## 文件关联（可选）

运行以下命令后，双击任意 `.hxg` 文件将用编码器打开（仅当前用户，无需管理员）：

```powershell
powershell -ExecutionPolicy Bypass -File register_filetype.ps1
```

撤销：`unregister_filetype.ps1`

图标文件 `hx.ico` 由 `make_icon.py` 生成（需要 Pillow）。

## HX Studio 界面

界面布局仿照 VS Code：

| 区域 | 说明 |
|---|---|
| 菜单栏 | 文件 / 编辑 / 运行 / 视图 / 帮助 |
| 活动栏 | 资源管理器、搜索、小智、设置 |
| 侧边栏 | 项目内 `.hxg` 文件列表，点击打开 |
| 标签页 | 当前文件名 + 关闭按钮 |
| 面包屑 | 显示文件所在路径 |
| 底部面板 | 输出 / 变量 / 问题 三标签切换 |
| 状态栏 | 分支、错误数、光标位置、编码、语言 |
| 右侧 | 小智 AI 助手 |

快捷键：`F5` 运行、`F10` 单步、`Ctrl+O` 打开、`Ctrl+S` 保存、`Ctrl+N` 新建、`Ctrl+B` 切换侧边栏。

## 图形绘制

用代码画图，无需额外依赖（基于 tkinter）：

```hx
gwin(600, 400);                          # 创建窗口
grect(0, 0, 600, 400, "white", "lightcyan");
gcircle(300, 200, 80, "orange", "gold"); # 圆
gline(50, 350, 550, 350, "blue", 3);     # 线
gtext(250, 50, "Hello!", "navy");        # 文字
gsleep(500);                             # 刷新并暂停
```

完整示例见 `graphics.hxg`。

## 交互与系统能力

### 鼠标键盘事件

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

on_click(x, y) { gcircle(x, y, 10, "red", "red"); }
gclick(on_click);
```

键名：字母/数字为自身，特殊键为 `space` `enter` `esc` `backspace` `tab` `Up` `Down` 等。

### 文件读写

```hx
writefile("out.txt", "你好\n");
appendfile("out.txt", "追加一行\n");
s = readfile("out.txt");
print(s);

if (exists("out.txt")) {
  print("文件存在");
}

列表 = files(".");
for (i = 0; i < len(列表); i += 1) { print(列表[i]); }
```

### 打开文件与程序

```hx
openfile("out.txt");              # 用默认程序打开
openurl("https://example.com");   # 用浏览器打开
runapp("notepad.exe");            # 启动程序
```

## 内置 AI 助手「小智」

编辑器右侧内置了 AI 编程向导「小智」，帮助你在 HX 语言的世界里闯荡。

- 点击右上角 ⚙ 配置 API（支持 DeepSeek / Kimi / 通义 / 智谱 / Ollama 等 OpenAI 兼容服务）
- 配置保存在 `%APPDATA%\HXLanguage\config.json`
- 默认勾选「附带当前代码」，小智能直接看到你正在写的程序
- 回复**流式输出**，逐字显示，不用等全部生成完
- 小智返回的代码块可双击下方「📋 双击此处插入代码」一键插入编辑器

## 项目结构

```
hx.py                    解释器 + Tkinter 图形编码器（含小智 AI 助手）
demo.hxg / t.hxg / f4.hxg / auto.hxg   示例程序
graphics.hxg             图形绘制示例
hx.ico                   .hxg 文件图标
make_icon.py             图标生成脚本
register_filetype.ps1    Windows 文件关联注册
unregister_filetype.ps1  撤销文件关联
```
