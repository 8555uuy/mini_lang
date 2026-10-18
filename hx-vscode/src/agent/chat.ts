import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getApiKey, getApiConfig, findInterpreter } from '../extension';
import { runFileCapture } from '../runner';

/**
 * 小智的备用实现（不依赖 Webview）
 * 用 OutputChannel 显示对话流，InputBox 接收输入
 * 兼容不支持 Webview 的编辑器（如某些 VS Code 衍生版）
 */

const TOOLS = [
    {
        type: 'function',
        function: {
            name: 'read_file',
            description: '读取项目内的文件内容',
            parameters: {
                type: 'object',
                properties: { path: { type: 'string', description: '相对项目根目录的文件路径' } },
                required: ['path']
            }
        }
    },
    {
        type: 'function',
        function: {
            name: 'write_file',
            description: '写入文件（会覆盖已有内容），写完自动在编辑器打开',
            parameters: {
                type: 'object',
                properties: {
                    path: { type: 'string', description: '相对项目根目录的文件路径' },
                    content: { type: 'string', description: '完整文件内容' }
                },
                required: ['path', 'content']
            }
        }
    },
    {
        type: 'function',
        function: {
            name: 'run_hx',
            description: '运行一个 HX 文件并返回输出',
            parameters: {
                type: 'object',
                properties: { path: { type: 'string', description: '相对项目根目录的 .hxg 文件路径' } },
                required: ['path']
            }
        }
    },
    {
        type: 'function',
        function: {
            name: 'list_files',
            description: '列出项目内的 .hxg 文件',
            parameters: { type: 'object', properties: {} }
        }
    },
    {
        type: 'function',
        function: {
            name: 'get_editor',
            description: '读取当前编辑器里正在编辑的 HX 代码',
            parameters: { type: 'object', properties: {} }
        }
    }
];

const SYSTEM_PROMPT = `你是小智，HX 语言的编程助手，运行在 VS Code 里。

HX 语言语法要点：
- 变量直接赋值即声明：x = 10;  s = "hi";  arr = [1,2,3];  d = {a:1};
- 函数（C 风格）：add(a, b) { return a + b; }  没有 fn 关键字
- 条件：if (c) { } else if (c2) { } else { }（没有 elif）
- 循环：while (c) { }  /  for (i = 0; i < n; i += 1) { }  没有 for-in
- 异常：try { } catch (e) { }
- 逻辑：&& || ! 或 and or not
- 注释：#

内置函数：
- 类型 type；数组 len push min max abs range
- 字典 keys items has set；字符串 upper lower trim split join
- 转换 str num；数学 sqrt sin cos tan floor ceil round random PI
- 输入 print input scanf
- 图形 gwin gline grect gcircle gtext gclear gsleep
- 事件 gwaitkey gwaitclick gkeydown gclick
- 文件 readfile writefile appendfile exists files openfile openurl runapp
- 网络 http_get http_download bg_run md5 sha256 unzip zipinfo

UI 组件：uiwin uibtn uilabel uiheading uiinput uitext uicheck uiradio uicombo uilist uirange uiprogress uiimage uitable uipanel uiseparator uitabs
事件 uion(id, "click", fn)；uiget / uiset 读写值；uirun() 启动。

你有工具可以读文件、写文件、运行代码。写新文件用 write_file，改现有文件先 read_file 再整体写回。
代码块用 \`\`\`hx 包裹。回答简洁，直接给可运行的代码。`;

interface ChatMessage {
    role: 'system' | 'user' | 'assistant' | 'tool';
    content: string | null;
    tool_calls?: any[];
    tool_call_id?: string;
    name?: string;
}

export class ChatChannel {
    private channel: vscode.OutputChannel;
    private history: ChatMessage[] = [];
    private busy = false;

    constructor(private readonly context: vscode.ExtensionContext) {
        this.channel = vscode.window.createOutputChannel('HX 小智');
        this.history.push({ role: 'system', content: SYSTEM_PROMPT });
    }

    async start() {
        this.channel.show(true);
        this.channel.appendLine('');
        this.channel.appendLine('╭─────────────────────────────────────────────────────╮');
        this.channel.appendLine('│  小智 · HX 编程助手                                 │');
        this.channel.appendLine('╰─────────────────────────────────────────────────────╯');
        this.channel.appendLine('');
        this.channel.appendLine('输入问题即可。输入 /clear 清空对话，/api 配置 API Key，/run <文件> 运行文件。');
        this.channel.appendLine('');

        while (true) {
            if (this.busy) {
                await new Promise(r => setTimeout(r, 100));
                continue;
            }
            const input = await vscode.window.showInputBox({
                title: '小智',
                prompt: '输入问题（Enter 发送，Esc 关闭）',
                placeHolder: '比如：写一个冒泡排序',
                ignoreFocusOut: true,
            });
            if (input === undefined) {
                return;
            }
            const text = input.trim();
            if (!text) {
                continue;
            }
            if (text === '/clear') {
                this.history = [{ role: 'system', content: SYSTEM_PROMPT }];
                this.channel.clear();
                this.channel.appendLine('对话已清空。');
                continue;
            }
            if (text === '/api') {
                await vscode.commands.executeCommand('hx.setApiKey');
                continue;
            }
            if (text.startsWith('/run ')) {
                const file = text.slice(5).trim();
                await this.runFile(file);
                continue;
            }
            await this.chat(text);
        }
    }

    private async runFile(file: string) {
        const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!root) {
            this.channel.appendLine('没有打开的工作区');
            return;
        }
        const abs = path.resolve(root, file);
        const py = findInterpreter(this.context);
        if (!py) {
            this.channel.appendLine('找不到 hx.py');
            return;
        }
        this.channel.appendLine('── 运行 ' + file + ' ──');
        const r = await runFileCapture(abs, py);
        if (r.stdout) {
            this.channel.append(r.stdout);
        }
        if (r.stderr) {
            this.channel.appendLine('[stderr]');
            this.channel.append(r.stderr);
        }
        this.channel.appendLine('── 退出码 ' + r.code + ' ──');
        this.channel.appendLine('');
    }

    private async chat(text: string) {
        this.busy = true;
        try {
            const apiKey = await getApiKey(this.context);
            if (!apiKey) {
                this.channel.appendLine('[!] 未配置 API Key，执行 HX: 配置小智 API');
                return;
            }

            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'hx') {
                const code = editor.document.getText();
                if (code.trim()) {
                    this.history.push({
                        role: 'user',
                        content: '当前编辑器文件：' + path.basename(editor.document.uri.fsPath) + '\n\n' + code.slice(0, 8000)
                    });
                    this.history.push({ role: 'assistant', content: '收到，我会参考这段代码。' });
                }
            }

            this.history.push({ role: 'user', content: text });
            this.channel.appendLine('▸ 你：' + text);
            this.channel.appendLine('');

            for (let round = 0; round < 6; round++) {
                this.channel.append('▸ 小智：');
                const result = await this.streamChat();
                if (!result) {
                    break;
                }
                this.channel.appendLine('');

                const msg: ChatMessage = {
                    role: 'assistant',
                    content: result.content || null,
                    tool_calls: result.tool_calls.length ? result.tool_calls : undefined,
                };
                this.history.push(msg);

                if (!result.tool_calls.length) {
                    break;
                }

                for (const tc of result.tool_calls) {
                    const name = tc.function.name;
                    let args: any = {};
                    try {
                        args = JSON.parse(tc.function.arguments || '{}');
                    } catch {}
                    this.channel.appendLine('  ⟳ 调用 ' + name + '(' + JSON.stringify(args).slice(0, 80) + ')');
                    let output = '';
                    try {
                        output = await this.executeTool(name, args);
                    } catch (e: any) {
                        output = '工具执行失败：' + (e.message || String(e));
                    }
                    this.history.push({
                        role: 'tool',
                        content: output.slice(0, 8000),
                        tool_call_id: tc.id,
                        name,
                    });
                }
                this.channel.appendLine('');
            }
        } catch (e: any) {
            this.channel.appendLine('[错误] ' + (e.message || String(e)));
        } finally {
            this.busy = false;
            this.channel.appendLine('');
        }
    }

    private async executeTool(name: string, args: any): Promise<string> {
        const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!root) {
            return '没有打开的工作区';
        }
        const safePath = (p: string) => {
            const abs = path.resolve(root, p);
            if (!abs.startsWith(path.resolve(root))) {
                throw new Error('路径越界：' + p);
            }
            return abs;
        };

        switch (name) {
            case 'read_file': {
                const abs = safePath(args.path);
                if (!fs.existsSync(abs)) {
                    return '文件不存在：' + args.path;
                }
                return fs.readFileSync(abs, 'utf-8');
            }
            case 'write_file': {
                const abs = safePath(args.path);
                fs.mkdirSync(path.dirname(abs), { recursive: true });
                fs.writeFileSync(abs, args.content, 'utf-8');
                const doc = await vscode.workspace.openTextDocument(abs);
                await vscode.window.showTextDocument(doc, { preview: false });
                return '已写入 ' + args.path + '（' + args.content.length + ' 字符）';
            }
            case 'run_hx': {
                const abs = safePath(args.path);
                const py = findInterpreter(this.context);
                if (!py) {
                    return '找不到 hx.py';
                }
                const r = await runFileCapture(abs, py);
                return '退出码 ' + r.code + '\n' + r.stdout + (r.stderr ? '\n[stderr]\n' + r.stderr : '');
            }
            case 'list_files': {
                try {
                    return fs.readdirSync(root).filter(f => f.endsWith('.hxg')).join('\n') || '（无 .hxg 文件）';
                } catch {
                    return '读取目录失败';
                }
            }
            case 'get_editor': {
                const editor = vscode.window.activeTextEditor;
                if (!editor || editor.document.languageId !== 'hx') {
                    return '当前没有打开 HX 文件';
                }
                return editor.document.getText();
            }
        }
        return '未知工具：' + name;
    }

    private streamChat(): Promise<{ content: string; tool_calls: any[] } | null> {
        return new Promise(async (resolve, reject) => {
            const cfg = getApiConfig();
            const apiKey = await getApiKey(this.context);
            const endpoint = cfg.baseUrl.replace(/\/$/, '') + '/chat/completions';

            const https = require('https');
            const http = require('http');
            const url = new URL(endpoint);
            const lib = url.protocol === 'https:' ? https : http;
            const payload = JSON.stringify({
                model: cfg.model,
                messages: this.history,
                tools: TOOLS,
                stream: true,
                temperature: 0.3,
            });

            const req = lib.request({
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: url.pathname + url.search,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + apiKey,
                    'Content-Length': Buffer.byteLength(payload),
                    'Accept': 'text/event-stream',
                },
            }, (res: any) => {
                if (res.statusCode !== 200) {
                    let errBody = '';
                    res.on('data', (c: Buffer) => { errBody += c.toString(); });
                    res.on('end', () => {
                        this.channel.appendLine('HTTP ' + res.statusCode + ': ' + errBody.slice(0, 300));
                        resolve(null);
                    });
                    return;
                }
                let content = '';
                const toolCalls: any[] = [];
                let buffer = '';

                res.on('data', (chunk: Buffer) => {
                    buffer += chunk.toString('utf-8');
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith('data:')) {
                            continue;
                        }
                        const data = trimmed.slice(5).trim();
                        if (data === '[DONE]') {
                            continue;
                        }
                        try {
                            const j = JSON.parse(data);
                            const delta = j.choices?.[0]?.delta;
                            if (!delta) {
                                continue;
                            }
                            if (delta.content) {
                                content += delta.content;
                                this.channel.append(delta.content);
                            }
                            if (delta.tool_calls) {
                                for (const tc of delta.tool_calls) {
                                    const idx = tc.index ?? 0;
                                    if (!toolCalls[idx]) {
                                        toolCalls[idx] = { id: tc.id || '', type: 'function', function: { name: '', arguments: '' } };
                                    }
                                    if (tc.id) {
                                        toolCalls[idx].id = tc.id;
                                    }
                                    if (tc.function?.name) {
                                        toolCalls[idx].function.name += tc.function.name;
                                    }
                                    if (tc.function?.arguments) {
                                        toolCalls[idx].function.arguments += tc.function.arguments;
                                    }
                                }
                            }
                        } catch {}
                    }
                });

                res.on('end', () => {
                    resolve({ content, tool_calls: toolCalls.filter(Boolean) });
                });
                res.on('error', (e: Error) => {
                    reject(e);
                });
            });

            req.on('error', (e: Error) => {
                reject(e);
            });
            req.write(payload);
            req.end();
        });
    }

    dispose() {
        this.channel.dispose();
    }
}
