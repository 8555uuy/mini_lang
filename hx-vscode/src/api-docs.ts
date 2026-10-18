/**
 * HX 内置函数完整字典
 * 用于 API 速查面板和补全提示
 */

export interface ApiEntry {
    name: string;
    sig: string;
    desc: string;
    example?: string;
    category: string;
}

export interface ApiCategory {
    name: string;
    icon: string;
    entries: ApiEntry[];
}

export const API_DOCS: ApiCategory[] = [
    {
        name: '类型与转换',
        icon: 'T',
        entries: [
            { name: 'type', sig: 'type(x)', desc: '返回值的类型名', example: 'print(type(42));  # 数字', category: '类型与转换' },
            { name: 'str', sig: 'str(x)', desc: '转换为字符串', example: 'print(str(42) + "!");', category: '类型与转换' },
            { name: 'num', sig: 'num(x)', desc: '转换为数字', example: 'n = num("3.14");', category: '类型与转换' },
        ],
    },
    {
        name: '输出与输入',
        icon: 'I/O',
        entries: [
            { name: 'print', sig: 'print(...args)', desc: '输出多个值，空格分隔', example: 'print("hi", 1, true);', category: '输出与输入' },
            { name: 'input', sig: 'input(prompt?)', desc: '读一行输入，返回字符串', example: 'name = input("你的名字：");', category: '输出与输入' },
            { name: 'scanf', sig: 'scanf(fmt, ...vars)', desc: '按格式读入多个值。格式符：%d 整数 / %f 数字 / %s 字符串 / %c 单字符。变量需先声明', example: 'a = 0; b = 0;\nscanf("%d %d", a, b);', category: '输出与输入' },
            { name: 'help', sig: 'help()', desc: '打印语法速查', example: 'help();', category: '输出与输入' },
        ],
    },
    {
        name: '数组',
        icon: '[]',
        entries: [
            { name: 'len', sig: 'len(arr)', desc: '数组、字典或字符串的长度', example: 'print(len([1,2,3]));  # 3', category: '数组' },
            { name: 'push', sig: 'push(arr, v)', desc: '向数组末尾追加元素，返回数组', example: 'arr = [1,2];\npush(arr, 3);', category: '数组' },
            { name: 'range', sig: 'range(n)', desc: '返回 [0, 1, ..., n-1]', example: 'for (i = 0; i < len(range(5)); i += 1) {}', category: '数组' },
            { name: 'min', sig: 'min(a, b) / min(arr)', desc: '最小值', example: 'print(min([3,1,4]));', category: '数组' },
            { name: 'max', sig: 'max(a, b) / max(arr)', desc: '最大值', example: 'print(max(3, 5));', category: '数组' },
            { name: 'abs', sig: 'abs(x)', desc: '绝对值', example: 'print(abs(-5));', category: '数组' },
        ],
    },
    {
        name: '字典',
        icon: '{}',
        entries: [
            { name: 'keys', sig: 'keys(dict)', desc: '返回字典所有键（数组）', example: 'd = {a:1, b:2};\nks = keys(d);', category: '字典' },
            { name: 'items', sig: 'items(dict)', desc: '返回 [[键, 值], ...]', example: 'for (i = 0; i < len(items(d)); i += 1) {}\n', category: '字典' },
            { name: 'has', sig: 'has(x, k)', desc: '判断数组/字典/字符串是否包含 k', example: 'if (has(d, "name")) { print("有"); }', category: '字典' },
            { name: 'set', sig: 'set(dict, k, v)', desc: '设置字典键值，返回字典', example: 'set(d, "new", 100);', category: '字典' },
        ],
    },
    {
        name: '字符串',
        icon: 'S',
        entries: [
            { name: 'upper', sig: 'upper(s)', desc: '转大写', example: 'print(upper("abc"));  # ABC', category: '字符串' },
            { name: 'lower', sig: 'lower(s)', desc: '转小写', example: 'print(lower("ABC"));  # abc', category: '字符串' },
            { name: 'trim', sig: 'trim(s)', desc: '去除首尾空白', example: 'print(trim("  hi  "));', category: '字符串' },
            { name: 'split', sig: 'split(s, sep)', desc: '按分隔符切分为数组', example: 'parts = split("a,b,c", ",");', category: '字符串' },
            { name: 'join', sig: 'join(arr, sep)', desc: '用分隔符把数组连成字符串', example: 'print(join(["a","b"], "-"));  # a-b', category: '字符串' },
        ],
    },
    {
        name: '数学',
        icon: 'fx',
        entries: [
            { name: 'sqrt', sig: 'sqrt(x)', desc: '平方根', example: 'print(sqrt(16));  # 4', category: '数学' },
            { name: 'sin', sig: 'sin(x)', desc: '正弦（弧度）', example: 'print(sin(PI / 2));', category: '数学' },
            { name: 'cos', sig: 'cos(x)', desc: '余弦（弧度）', example: 'print(cos(0));', category: '数学' },
            { name: 'tan', sig: 'tan(x)', desc: '正切（弧度）', example: 'print(tan(0));', category: '数学' },
            { name: 'floor', sig: 'floor(x)', desc: '向下取整', example: 'print(floor(3.9));  # 3', category: '数学' },
            { name: 'ceil', sig: 'ceil(x)', desc: '向上取整', example: 'print(ceil(3.1));  # 4', category: '数学' },
            { name: 'round', sig: 'round(x)', desc: '四舍五入', example: 'print(round(3.5));  # 4', category: '数学' },
            { name: 'random', sig: 'random()', desc: '返回 [0, 1) 的随机数', example: 'print(random());', category: '数学' },
            { name: 'PI', sig: 'PI', desc: '圆周率常量 3.141592653589793', example: 'area = PI * r * r;', category: '数学' },
        ],
    },
    {
        name: '图形绘制',
        icon: '✎',
        entries: [
            { name: 'gwin', sig: 'gwin(w, h, title?)', desc: '创建图形窗口', example: 'gwin(600, 400, "画板");', category: '图形绘制' },
            { name: 'gline', sig: 'gline(x1, y1, x2, y2, color?, width?)', desc: '画线', example: 'gline(0, 0, 100, 100, "red", 3);', category: '图形绘制' },
            { name: 'grect', sig: 'grect(x1, y1, x2, y2, color?, fill?)', desc: '画矩形', example: 'grect(10, 10, 110, 60, "black", "lightblue");', category: '图形绘制' },
            { name: 'gcircle', sig: 'gcircle(cx, cy, r, color?, fill?)', desc: '画圆', example: 'gcircle(200, 200, 50, "navy", "gold");', category: '图形绘制' },
            { name: 'gtext', sig: 'gtext(x, y, text, color?)', desc: '写文字', example: 'gtext(20, 20, "Hello", "black");', category: '图形绘制' },
            { name: 'gclear', sig: 'gclear()', desc: '清空画布', example: 'gclear();', category: '图形绘制' },
            { name: 'gsleep', sig: 'gsleep(ms)', desc: '刷新并暂停指定毫秒', example: 'gsleep(1000);', category: '图形绘制' },
        ],
    },
    {
        name: '事件',
        icon: '!',
        entries: [
            { name: 'gwaitkey', sig: 'gwaitkey(timeout?)', desc: '阻塞等待按键，返回键名；超时返回 ""', example: 'k = gwaitkey(3000);', category: '事件' },
            { name: 'gwaitclick', sig: 'gwaitclick(timeout?)', desc: '阻塞等待点击，返回 [x, y]；超时返回 []', example: 'p = gwaitclick(3000);', category: '事件' },
            { name: 'gkeydown', sig: 'gkeydown(fn)', desc: '绑定按键回调，fn(key)', example: 'on_key(k) { print(k); }\ngkeydown(on_key);', category: '事件' },
            { name: 'gclick', sig: 'gclick(fn)', desc: '绑定点击回调，fn(x, y)', example: 'on_c(x, y) { print(x, y); }\ngclick(on_c);', category: '事件' },
        ],
    },
    {
        name: 'UI 组件',
        icon: 'UI',
        entries: [
            { name: 'uiwin', sig: 'uiwin(w, h, title)', desc: '创建 UI 窗口', example: 'uiwin(400, 300, "我的界面");', category: 'UI 组件' },
            { name: 'uiheading', sig: 'uiheading(id, x, y, w, h, text)', desc: '标题（大号粗体）', example: 'uiheading("h1", 20, 20, 300, 36, "标题");', category: 'UI 组件' },
            { name: 'uilabel', sig: 'uilabel(id, x, y, w, h, text)', desc: '标签', example: 'uilabel("lb", 20, 60, 120, 26, "用户名：");', category: 'UI 组件' },
            { name: 'uibtn', sig: 'uibtn(id, x, y, w, h, text)', desc: '按钮', example: 'uibtn("ok", 20, 100, 100, 32, "确定");', category: 'UI 组件' },
            { name: 'uiinput', sig: 'uiinput(id, x, y, w, h)', desc: '单行输入框', example: 'uiinput("inp", 100, 60, 200, 28);', category: 'UI 组件' },
            { name: 'uitext', sig: 'uitext(id, x, y, w, h)', desc: '多行文本', example: 'uitext("txt", 20, 140, 300, 100);', category: 'UI 组件' },
            { name: 'uicheck', sig: 'uicheck(id, x, y, text)', desc: '勾选框', example: 'uicheck("ck", 20, 250, "记住我");', category: 'UI 组件' },
            { name: 'uiradio', sig: 'uiradio(id, x, y, w, h, items)', desc: '单选组', example: 'uiradio("r", 20, 280, 160, 78, ["A", "B", "C"]);', category: 'UI 组件' },
            { name: 'uicombo', sig: 'uicombo(id, x, y, w, h, items)', desc: '下拉框', example: 'uicombo("cb", 200, 280, 160, 28, ["北京", "上海"]);', category: 'UI 组件' },
            { name: 'uilist', sig: 'uilist(id, x, y, w, h, items)', desc: '列表框', example: 'uilist("ls", 20, 370, 160, 100, ["项1", "项2"]);', category: 'UI 组件' },
            { name: 'uirange', sig: 'uirange(id, x, y, w, max)', desc: '水平滑块', example: 'uirange("rg", 20, 480, 200, 100);', category: 'UI 组件' },
            { name: 'uiprogress', sig: 'uiprogress(id, x, y, w, h)', desc: '进度条（0-100）', example: 'uiprogress("pg", 20, 520, 200, 18);\nuiset("pg", 60);', category: 'UI 组件' },
            { name: 'uiimage', sig: 'uiimage(id, x, y, w, h)', desc: '图片框（用 uiset 传路径）', example: 'uiimage("img", 240, 370, 160, 120);\nuiset("img", "photo.png");', category: 'UI 组件' },
            { name: 'uitable', sig: 'uitable(id, x, y, w, h, columns)', desc: '表格', example: 'uitable("tb", 20, 550, 400, 120, ["姓名", "年龄"]);', category: 'UI 组件' },
            { name: 'uipanel', sig: 'uipanel(id, x, y, w, h)', desc: '面板容器', example: 'uipanel("pn", 240, 480, 200, 60);', category: 'UI 组件' },
            { name: 'uiseparator', sig: 'uiseparator(id, x, y, w)', desc: '水平分割线', example: 'uiseparator("sep", 20, 130, 360);', category: 'UI 组件' },
            { name: 'uitabs', sig: 'uitabs(id, x, y, w, h, items)', desc: '标签页', example: 'uitabs("tab", 20, 680, 400, 160, ["页1", "页2"]);', category: 'UI 组件' },
            { name: 'uion', sig: 'uion(id, event, fn)', desc: '绑定事件。event 为 click / change / select', example: 'on_click() { print("点击"); }\nuion("ok", "click", on_click);', category: 'UI 组件' },
            { name: 'uiget', sig: 'uiget(id)', desc: '读取组件值', example: 'v = uiget("inp");', category: 'UI 组件' },
            { name: 'uiset', sig: 'uiset(id, value)', desc: '设置组件值', example: 'uiset("lb", "新文字");', category: 'UI 组件' },
            { name: 'uirun', sig: 'uirun()', desc: '启动 UI 事件循环', example: 'uirun();', category: 'UI 组件' },
        ],
    },
    {
        name: '网络',
        icon: 'NET',
        entries: [
            { name: 'http_get', sig: 'http_get(url, timeout?)', desc: '同步 GET，返回文本', example: 's = http_get("https://example.com");', category: '网络' },
            { name: 'http_download', sig: 'http_download(url, path, timeout?)', desc: '同步下载，返回字节数', example: 'n = http_download("https://x/a.zip", "a.zip");', category: '网络' },
            { name: 'bg_run', sig: 'bg_run(fn, ...args, callback)', desc: '后台执行内置 IO 函数，完成后主线程回调。后台不能操作 UI，回调里可以', example: 'on_done(t) { print(len(t)); }\nbg_run(http_get, "https://x", on_done);', category: '网络' },
        ],
    },
    {
        name: '压缩与哈希',
        icon: 'ZIP',
        entries: [
            { name: 'md5', sig: 'md5(path)', desc: '文件 MD5（32 位十六进制）', example: 'print(md5("a.txt"));', category: '压缩与哈希' },
            { name: 'sha256', sig: 'sha256(path)', desc: '文件 SHA256（64 位十六进制）', example: 'print(sha256("a.txt"));', category: '压缩与哈希' },
            { name: 'unzip', sig: 'unzip(path, dest)', desc: '解压 zip 到目录，返回文件数。防 Zip Slip', example: 'n = unzip("a.zip", "out");', category: '压缩与哈希' },
            { name: 'zipinfo', sig: 'zipinfo(path)', desc: '返回 [[名称, 大小], ...]', example: 'info = zipinfo("a.zip");', category: '压缩与哈希' },
        ],
    },
    {
        name: '文件与系统',
        icon: 'DIR',
        entries: [
            { name: 'readfile', sig: 'readfile(path)', desc: '读文本文件（UTF-8）', example: 's = readfile("a.txt");', category: '文件与系统' },
            { name: 'writefile', sig: 'writefile(path, content)', desc: '写文件（覆盖），自动创建父目录', example: 'writefile("a.txt", "hello");', category: '文件与系统' },
            { name: 'appendfile', sig: 'appendfile(path, content)', desc: '追加到文件末尾', example: 'appendfile("log.txt", "一行\n");', category: '文件与系统' },
            { name: 'exists', sig: 'exists(path)', desc: '文件或目录是否存在', example: 'if (exists("a.txt")) { print("有"); }', category: '文件与系统' },
            { name: 'files', sig: 'files(dir)', desc: '列出目录内容（数组）', example: 'fs = files(".");', category: '文件与系统' },
            { name: 'openfile', sig: 'openfile(path)', desc: '用系统默认程序打开文件', example: 'openfile("a.txt");', category: '文件与系统' },
            { name: 'openurl', sig: 'openurl(url)', desc: '用浏览器打开网址', example: 'openurl("https://example.com");', category: '文件与系统' },
            { name: 'runapp', sig: 'runapp(cmd)', desc: '启动外部程序', example: 'runapp("notepad.exe");', category: '文件与系统' },
        ],
    },
];
