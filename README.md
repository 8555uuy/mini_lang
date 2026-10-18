# MiniLang / HX 语言

一个用 Python 实现的迷你脚本语言解释器，附带 Tkinter 图形编码器。

## 特性

- **自动类型推断**：直接写 `x = 10;` 即可，无需声明类型
- **带括号的控制流**：`if (...)` / `while (...)` / `for (...)`
- **两种 for 循环**：遍历式 `for (x in arr)` 与 C 式三段 `for (i = 0; i < n; i += 1)`
- **异常处理**：`try { ... } catch (e) { ... }`
- **字符串插值**：`"hi ${x}!"`
- **丰富数据结构**：数组、字典、函数、闭包
- **图形编码器**：语法高亮、行号、错误红色波浪线、单步调试、变量观察

## 快速开始

```bash
# 命令行运行
python hx.py demo.hx

# 打开图形编码器
python hx.py

# 用编码器打开指定文件
python hx.py --edit demo.hx
```

## 语法速览

```hx
# 变量：直接赋值，自动判断类型
x = 10;
s = "hello";
arr = [1, 2, 3];
d = {name: "hx", ver: 3};

# 函数
fn fib(n) {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}

print("fib(10) =", fib(10));

# 条件
if (x > 5) {
  print("big");
} elif (x > 0) {
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

# for - 遍历式
for (k in d) { print("key:", k); }

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

## 文件关联（可选）

运行以下命令后，双击任意 `.hx` 文件将用编码器打开（仅当前用户，无需管理员）：

```powershell
powershell -ExecutionPolicy Bypass -File register_filetype.ps1
```

撤销：`unregister_filetype.ps1`

图标文件 `hx.ico` 由 `make_icon.py` 生成（需要 Pillow）。

## 项目结构

```
hx.py                    解释器 + Tkinter 图形编码器
demo.hx / t.hx / f4.hx / auto.hx   示例程序
hx.ico                   .hx 文件图标
make_icon.py             图标生成脚本
register_filetype.ps1    Windows 文件关联注册
unregister_filetype.ps1  撤销文件关联
```
