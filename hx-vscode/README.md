# HX Language

HX 语言官方 VS Code 扩展。

## 功能

- **语法高亮**：关键字、字符串、数字、注释、内置函数、UI 组件分色显示
- **智能补全**：输入时自动提示内置函数、UI 组件、关键字
- **悬停文档**：鼠标悬停在函数名上显示签名和说明
- **代码片段**：输入 fn、for、uiwin-full 等触发
- **运行**：F5 或点击右上角 ▶ 在集成终端运行当前文件
- **小智 Agent**：AI 编程助手，能读文件、写文件、运行代码
- **UI 画板**：可视化拖放 16 种组件，一键生成 HX 代码

## 命令

| 命令 | 说明 |
|---|---|
| HX: 运行当前文件 | 在终端运行当前 .hxg |
| HX: 打开小智 | 打开 AI 助手面板 |
| HX: 打开 UI 画板 | 打开可视化设计器 |
| HX: 配置小智 API | 保存 API Key 到 VS Code 加密存储 |
| HX: 语法速查 | 打开完整语法文档 |

## 配置

| 设置 | 默认 | 说明 |
|---|---|---|
| hx.pythonPath | python | 运行解释器的 Python 路径 |
| hx.interpreterPath | 空 | hx.py 的绝对路径，留空自动查找 |
| hx.ai.baseUrl | https://api.deepseek.com/v1 | AI 接口地址 |
| hx.ai.model | deepseek-chat | 模型名 |

## 快速开始

1. 安装扩展
2. 打开任意 .hxg 文件
3. 按 F5 运行，或点右上角 ▶
4. 点状态栏「小智」打开 AI 助手
5. Ctrl+Shift+P → HX: 打开 UI 画板 可视化设计界面

## 小智 Agent

小智能主动调用工具完成任务：

- **read_file**：读取项目文件
- **write_file**：写文件（自动在编辑器打开）
- **run_hx**：运行 HX 文件并查看输出
- **list_files**：列出 .hxg 文件
- **get_editor**：读取当前编辑器代码

比如输入「写一个贪吃蛇游戏」，小智会直接生成 snake.hxg 并运行给你看。

## 依赖

- Python 3.8+
- PyQt5（UI 组件需要）
- tkinter（图形绘制需要，Python 自带）
