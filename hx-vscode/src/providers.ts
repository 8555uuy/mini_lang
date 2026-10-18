import * as vscode from 'vscode';

/** HX 内置函数签名表 */
const BUILTINS: Record<string, { sig: string; doc: string }> = {
    print: { sig: 'print(...args)', doc: '输出多个值，用空格分隔' },
    input: { sig: 'input(prompt)', doc: '读一行输入，返回字符串' },
    scanf: { sig: 'scanf(fmt, ...vars)', doc: '按格式读入：%d 整数 / %f 数字 / %s 字符串 / %c 单字符\n变量需先声明' },
    help: { sig: 'help()', doc: '打印语法速查' },
    type: { sig: 'type(x)', doc: '返回类型名：数字 / 字符串 / 布尔 / 数组 / 字典 / 函数 / 空' },
    len: { sig: 'len(x)', doc: '数组、字典或字符串的长度' },
    push: { sig: 'push(arr, v)', doc: '向数组末尾追加元素，返回数组' },
    keys: { sig: 'keys(dict)', doc: '返回字典的所有键（数组）' },
    items: { sig: 'items(dict)', doc: '返回 [[键, 值], ...]' },
    has: { sig: 'has(x, k)', doc: '判断数组/字典/字符串是否包含 k' },
    set: { sig: 'set(dict, k, v)', doc: '设置字典的键值，返回字典' },
    str: { sig: 'str(x)', doc: '转为字符串' },
    num: { sig: 'num(x)', doc: '转为数字' },
    upper: { sig: 'upper(s)', doc: '转大写' },
    lower: { sig: 'lower(s)', doc: '转小写' },
    trim: { sig: 'trim(s)', doc: '去除首尾空白' },
    split: { sig: 'split(s, sep)', doc: '按分隔符切分为数组' },
    join: { sig: 'join(arr, sep)', doc: '用分隔符把数组连成字符串' },
    min: { sig: 'min(a, b) / min(arr)', doc: '最小值' },
    max: { sig: 'max(a, b) / max(arr)', doc: '最大值' },
    abs: { sig: 'abs(x)', doc: '绝对值' },
    sqrt: { sig: 'sqrt(x)', doc: '平方根' },
    sin: { sig: 'sin(x)', doc: '正弦（弧度）' },
    cos: { sig: 'cos(x)', doc: '余弦（弧度）' },
    tan: { sig: 'tan(x)', doc: '正切（弧度）' },
    floor: { sig: 'floor(x)', doc: '向下取整' },
    ceil: { sig: 'ceil(x)', doc: '向上取整' },
    round: { sig: 'round(x)', doc: '四舍五入' },
    random: { sig: 'random()', doc: '返回 [0, 1) 的随机数' },
    range: { sig: 'range(n)', doc: '返回 [0, 1, ..., n-1]' },
    PI: { sig: 'PI', doc: '圆周率常量' },

    gwin: { sig: 'gwin(w, h, title?)', doc: '创建图形窗口' },
    gline: { sig: 'gline(x1, y1, x2, y2, color?, width?)', doc: '画线' },
    grect: { sig: 'grect(x1, y1, x2, y2, color?, fill?)', doc: '画矩形' },
    gcircle: { sig: 'gcircle(cx, cy, r, color?, fill?)', doc: '画圆' },
    gtext: { sig: 'gtext(x, y, text, color?)', doc: '写文字' },
    gclear: { sig: 'gclear()', doc: '清空画布' },
    gsleep: { sig: 'gsleep(ms)', doc: '刷新并暂停指定毫秒' },
    gwaitkey: { sig: 'gwaitkey(timeout?)', doc: '阻塞等待按键，返回键名；超时返回 ""' },
    gwaitclick: { sig: 'gwaitclick(timeout?)', doc: '阻塞等待点击，返回 [x, y]；超时返回 []' },
    gkeydown: { sig: 'gkeydown(fn)', doc: '绑定按键回调，fn(key)' },
    gclick: { sig: 'gclick(fn)', doc: '绑定点击回调，fn(x, y)' },

    readfile: { sig: 'readfile(path)', doc: '读文本文件（UTF-8）' },
    writefile: { sig: 'writefile(path, content)', doc: '写文件（覆盖），自动创建目录' },
    appendfile: { sig: 'appendfile(path, content)', doc: '追加到文件末尾' },
    exists: { sig: 'exists(path)', doc: '文件或目录是否存在' },
    files: { sig: 'files(dir)', doc: '列出目录内容（数组）' },
    openfile: { sig: 'openfile(path)', doc: '用系统默认程序打开文件' },
    openurl: { sig: 'openurl(url)', doc: '用浏览器打开网址' },
    runapp: { sig: 'runapp(cmd)', doc: '启动外部程序' },

    http_get: { sig: 'http_get(url, timeout?)', doc: '同步 GET，返回文本' },
    http_download: { sig: 'http_download(url, path, timeout?)', doc: '同步下载，返回字节数' },
    bg_run: { sig: 'bg_run(fn, ...args, callback)', doc: '后台执行内置 IO 函数，完成后主线程回调' },
    md5: { sig: 'md5(path)', doc: '文件 MD5' },
    sha256: { sig: 'sha256(path)', doc: '文件 SHA256' },
    unzip: { sig: 'unzip(path, dest)', doc: '解压 zip 到目录，返回文件数' },
    zipinfo: { sig: 'zipinfo(path)', doc: '返回 [[名称, 大小], ...]' },

    uiwin: { sig: 'uiwin(w, h, title)', doc: '创建 UI 窗口' },
    uibtn: { sig: 'uibtn(id, x, y, w, h, text)', doc: '按钮' },
    uilabel: { sig: 'uilabel(id, x, y, w, h, text)', doc: '标签' },
    uiheading: { sig: 'uiheading(id, x, y, w, h, text)', doc: '标题（大号粗体）' },
    uiinput: { sig: 'uiinput(id, x, y, w, h)', doc: '单行输入框' },
    uitext: { sig: 'uitext(id, x, y, w, h)', doc: '多行文本' },
    uicheck: { sig: 'uicheck(id, x, y, text)', doc: '勾选框' },
    uiradio: { sig: 'uiradio(id, x, y, w, h, items)', doc: '单选组，items 是字符串数组' },
    uicombo: { sig: 'uicombo(id, x, y, w, h, items)', doc: '下拉框' },
    uilist: { sig: 'uilist(id, x, y, w, h, items)', doc: '列表框' },
    uirange: { sig: 'uirange(id, x, y, w, max)', doc: '水平滑块' },
    uiprogress: { sig: 'uiprogress(id, x, y, w, h)', doc: '进度条（0-100）' },
    uiimage: { sig: 'uiimage(id, x, y, w, h)', doc: '图片框（用 uiset 传路径）' },
    uitable: { sig: 'uitable(id, x, y, w, h, columns)', doc: '表格' },
    uipanel: { sig: 'uipanel(id, x, y, w, h)', doc: '面板容器' },
    uiseparator: { sig: 'uiseparator(id, x, y, w)', doc: '水平分割线' },
    uitabs: { sig: 'uitabs(id, x, y, w, h, items)', doc: '标签页' },
    uion: { sig: 'uion(id, event, fn)', doc: '绑定事件，event 为 "click" / "change" / "select"' },
    uiget: { sig: 'uiget(id)', doc: '读取组件值' },
    uiset: { sig: 'uiset(id, value)', doc: '设置组件值' },
    uirun: { sig: 'uirun()', doc: '启动 UI 事件循环' },
};

/** UI 组件签名里的参数提示 */
const UI_FIELD_HINTS: Record<string, string> = {
    id: '组件标识（字符串）',
    x: '横坐标',
    y: '纵坐标',
    w: '宽度',
    h: '高度',
    text: '显示文字',
    items: '选项数组，如 ["A", "B"]',
    max: '最大值',
};

export class HxCompletionProvider implements vscode.CompletionItemProvider {
    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        for (const [name, info] of Object.entries(BUILTINS)) {
            const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Function);
            item.detail = info.sig;
            item.documentation = new vscode.MarkdownString(info.doc);
            item.insertText = new vscode.SnippetString(name + '(');
            items.push(item);
        }
        const kws = ['if', 'else', 'while', 'for', 'return', 'break', 'continue', 'try', 'catch', 'true', 'false', 'null', 'and', 'or', 'not', 'del'];
        for (const kw of kws) {
            items.push(new vscode.CompletionItem(kw, vscode.CompletionItemKind.Keyword));
        }
        return items;
    }
}

export class HxHoverProvider implements vscode.HoverProvider {
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.Hover | undefined {
        const range = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_]*/);
        if (!range) {
            return undefined;
        }
        const word = document.getText(range);
        const info = BUILTINS[word];
        if (!info) {
            return undefined;
        }
        const md = new vscode.MarkdownString();
        md.appendCodeblock(info.sig, 'hx');
        md.appendMarkdown('\n\n' + info.doc);
        return new vscode.Hover(md, range);
    }
}

/**
 * 用 hx.py 的 tokenizer 做括号/语法快速检查（异步，不阻塞）
 */
export function createDiagnostics(): vscode.DiagnosticCollection {
    return vscode.languages.createDiagnosticCollection('hx');
}
