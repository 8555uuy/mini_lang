import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getApiKey, getApiConfig, findInterpreter } from '../extension';
import { runFileCapture } from '../runner';

/** Agent 可调用的工具定义（OpenAI function calling 格式） */
const TOOLS = [
    {
        type: 'function',
        function: {
            name: 'read_file',
            description: '读取项目内的文件内容',
            parameters: {
                type: 'object',
                properties: {
                    path: { type: 'string', description: '相对项目根目录的文件路径' }
                },
                required: ['path']
            }
        }
    },
    {
        type: 'function',
        function: {
            name: 'write_file',
            description: '写入文件（会覆盖已有内容）。写完会自动在编辑器打开。',
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
                properties: {
                    path: { type: 'string', description: '相对项目根目录的 .hxg 文件路径' }
                },
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
- 变量直接赋值即声明，自动推断类型：x = 10;  s = "hi";  arr = [1,2,3];  d = {a:1};
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

UI 组件（16 种）：uiwin uibtn uilabel uiheading uiinput uitext uicheck uiradio uicombo uilist uirange uiprogress uiimage uitable uipanel uiseparator uitabs
事件 uion(id, "click", fn)；uiget / uiset 读写值；uirun() 启动。

你有工具可以读文件、写文件、运行代码。写新文件时用 write_file，改现有文件时先 read_file 再整体写回。
代码块用 \`\`\`hx 包裹。回答简洁，直接给可运行的代码。`;

interface ChatMessage {
    role: 'system' | 'user' | 'assistant' | 'tool';
    content: string | null;
    tool_calls?: any[];
    tool_call_id?: string;
    name?: string;
}

export class AgentPanel {
    public static currentPanel: AgentPanel | undefined;
    private readonly panel: vscode.WebviewPanel;
    private readonly context: vscode.ExtensionContext;
    private readonly disposables: vscode.Disposable[] = [];
    private history: ChatMessage[] = [];
    private busy = false;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.panel = vscode.window.createWebviewPanel(
            'hxAgent',
            'HX 小智',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [context.extensionUri],
            }
        );
        this.panel.webview.html = this.getHtml();
        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
        this.panel.webview.onDidReceiveMessage(
            (msg) => this.onMessage(msg),
            null,
            this.disposables
        );
        this.history.push({ role: 'system', content: SYSTEM_PROMPT });
    }

    reveal() {
        this.panel.reveal(vscode.ViewColumn.Beside);
    }

    onDidDispose(cb: () => void) {
        this.panel.onDidDispose(cb, null, this.disposables);
    }

    private post(type: string, data?: any) {
        this.panel.webview.postMessage({ type, data });
    }

    private async onMessage(msg: any) {
        if (msg.type === 'send') {
            await this.handleUserMessage(msg.text);
        } else if (msg.type === 'clear') {
            this.history = [{ role: 'system', content: SYSTEM_PROMPT }];
            this.post('cleared');
        } else if (msg.type === 'applyCode') {
            this.applyCodeToEditor(msg.code);
        } else if (msg.type === 'setApi') {
            vscode.commands.executeCommand('hx.setApiKey');
        }
    }

    private async handleUserMessage(text: string) {
        if (this.busy) {
            return;
        }
        this.busy = true;
        try {
            const apiKey = await getApiKey(this.context);
            if (!apiKey) {
                this.post('error', '请先配置 API Key（命令面板 → HX: 配置小智 API）');
                this.busy = false;
                return;
            }

            // 附带当前编辑器内容
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
            await this.runLoop();
        } catch (e: any) {
            this.post('error', e.message || String(e));
        } finally {
            this.busy = false;
            this.post('done');
        }
    }

    private async runLoop() {
        const cfg = getApiConfig();
        const apiKey = await getApiKey(this.context);
        const endpoint = cfg.baseUrl.replace(/\/$/, '') + '/chat/completions';

        for (let round = 0; round < 6; round++) {
            const body = {
                model: cfg.model,
                messages: this.history,
                tools: TOOLS,
                stream: true,
                temperature: 0.3,
            };

            const result = await this.streamChat(endpoint, apiKey, body);
            if (!result) {
                return;
            }

            const msg: ChatMessage = {
                role: 'assistant',
                content: result.content || null,
                tool_calls: result.tool_calls.length ? result.tool_calls : undefined,
            };
            this.history.push(msg);

            if (!result.tool_calls.length) {
                return;
            }

            // 执行工具
            for (const tc of result.tool_calls) {
                const name = tc.function.name;
                let args: any = {};
                try {
                    args = JSON.parse(tc.function.arguments || '{}');
                } catch {}

                this.post('tool', { name, args });
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
                return '退出码 ' + r.code + '\n--- 输出 ---\n' + r.stdout + (r.stderr ? '\n--- 错误 ---\n' + r.stderr : '');
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

    private async streamChat(endpoint: string, apiKey: string, body: any): Promise<{ content: string; tool_calls: any[] } | null> {
        return new Promise(async (resolve, reject) => {
            const https = require('https');
            const http = require('http');
            const url = new URL(endpoint);
            const lib = url.protocol === 'https:' ? https : http;
            const payload = JSON.stringify(body);

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
                        this.post('error', 'HTTP ' + res.statusCode + ': ' + errBody.slice(0, 300));
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
                                this.post('chunk', delta.content);
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

    private async applyCodeToEditor(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('没有打开的编辑器');
            return;
        }
        await editor.edit(b => b.insert(editor.selection.active, code));
    }

    private getHtml(): string {
        const nonce = String(Date.now());
        return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--vscode-font-family);
  font-size: 13px;
  color: var(--vscode-foreground);
  background: var(--vscode-editor-background);
  display: flex;
  flex-direction: column;
  height: 100vh;
}
#header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--vscode-panel-border);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
#header h1 { font-size: 13px; font-weight: 600; }
#header .sub { color: var(--vscode-descriptionForeground); font-size: 11px; }
#header .spacer { flex: 1; }
#header button {
  background: transparent;
  color: var(--vscode-foreground);
  border: 1px solid var(--vscode-panel-border);
  border-radius: 3px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
#header button:hover { background: var(--vscode-toolbar-hoverBackground); }
#chat {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.msg { display: flex; flex-direction: column; gap: 4px; }
.msg.user { align-items: flex-end; }
.msg .role {
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
  font-weight: 600;
}
.msg .bubble {
  max-width: 92%;
  padding: 8px 12px;
  border-radius: 6px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .bubble {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
}
.msg.assistant .bubble {
  background: var(--vscode-editorWidget-background);
  border: 1px solid var(--vscode-panel-border);
}
.msg.tool .bubble {
  background: transparent;
  border: 1px dashed var(--vscode-panel-border);
  color: var(--vscode-descriptionForeground);
  font-size: 12px;
  font-family: var(--vscode-editor-font-family);
}
.msg.error .bubble {
  background: var(--vscode-inputValidation-errorBackground);
  border: 1px solid var(--vscode-inputValidation-errorBorder);
  color: var(--vscode-errorForeground);
}
.code-block {
  position: relative;
  margin: 8px 0;
  background: var(--vscode-textCodeBlock-background);
  border: 1px solid var(--vscode-panel-border);
  border-radius: 4px;
  padding: 10px 12px;
  font-family: var(--vscode-editor-font-family);
  font-size: 12px;
  overflow-x: auto;
  white-space: pre;
}
.code-block .lang {
  position: absolute;
  top: 4px;
  right: 8px;
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
}
.code-block .apply {
  position: absolute;
  bottom: 4px;
  right: 6px;
  font-size: 10px;
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 3px;
  padding: 2px 8px;
  cursor: pointer;
  opacity: 0;
  transition: opacity .15s;
}
.code-block:hover .apply { opacity: 1; }
#input-area {
  border-top: 1px solid var(--vscode-panel-border);
  padding: 10px;
  flex-shrink: 0;
}
#input {
  width: 100%;
  min-height: 70px;
  max-height: 200px;
  resize: none;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, transparent);
  border-radius: 4px;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 13px;
  outline: none;
}
#input:focus { border-color: var(--vscode-focusBorder); }
#actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
}
#actions .hint {
  flex: 1;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
}
#actions button {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 3px;
  padding: 6px 16px;
  font-size: 12px;
  cursor: pointer;
}
#actions button:hover { background: var(--vscode-button-hoverBackground); }
#actions button:disabled { opacity: .5; cursor: default; }
#actions button.secondary {
  background: transparent;
  color: var(--vscode-foreground);
  border: 1px solid var(--vscode-panel-border);
}
.cursor::after {
  content: '▍';
  animation: blink 1s infinite;
}
@keyframes blink { 50% { opacity: 0; } }
</style>
</head>
<body>
<div id="header">
  <h1>小智</h1>
  <span class="sub">HX 编程助手</span>
  <span class="spacer"></span>
  <button id="btn-clear">清空对话</button>
  <button id="btn-api">设置 API</button>
</div>
<div id="chat"></div>
<div id="input-area">
  <textarea id="input" placeholder="问点什么，或让我帮你写代码… (Ctrl+Enter 发送)"></textarea>
  <div id="actions">
    <span class="hint">支持读文件 / 写文件 / 运行代码</span>
    <button id="btn-send">发送</button>
  </div>
</div>
<script nonce="${nonce}">
const vscode = acquireVsCodeApi();
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const btnSend = document.getElementById('btn-send');
const btnClear = document.getElementById('btn-clear');
const btnApi = document.getElementById('btn-api');

let currentBubble = null;
let currentText = '';

function addMsg(role, text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;
  const roleLabel = document.createElement('div');
  roleLabel.className = 'role';
  roleLabel.textContent = role === 'user' ? '你' : role === 'assistant' ? '小智' : role === 'tool' ? '工具' : '错误';
  wrap.appendChild(roleLabel);
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

function renderMarkdown(el, text) {
  // 极简 markdown：代码块 + 行内代码
  const parts = text.split(/(\`\`\`[a-zA-Z]*\n[\s\S]*?\`\`\`)/g);
  el.innerHTML = '';
  for (const p of parts) {
    if (p.startsWith('\`\`\`')) {
      const m = p.match(/^\`\`\`([a-zA-Z]*)\n([\s\S]*?)\`\`\`$/);
      if (m) {
        const lang = m[1] || 'hx';
        const code = m[2];
        const block = document.createElement('div');
        block.className = 'code-block';
        const codeText = document.createElement('div');
        codeText.textContent = code;
        block.appendChild(codeText);
        const langLabel = document.createElement('div');
        langLabel.className = 'lang';
        langLabel.textContent = lang;
        block.appendChild(langLabel);
        const applyBtn = document.createElement('button');
        applyBtn.className = 'apply';
        applyBtn.textContent = '插入';
        applyBtn.onclick = () => vscode.postMessage({ type: 'applyCode', code });
        block.appendChild(applyBtn);
        el.appendChild(block);
        continue;
      }
    }
    const span = document.createElement('span');
    span.textContent = p;
    el.appendChild(span);
  }
}

btnSend.onclick = () => send();
input.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter') {
    send();
  }
});
btnClear.onclick = () => {
  vscode.postMessage({ type: 'clear' });
};
btnApi.onclick = () => {
  vscode.postMessage({ type: 'setApi' });
};

function send() {
  const text = input.value.trim();
  if (!text) return;
  addMsg('user', text);
  input.value = '';
  btnSend.disabled = true;
  currentBubble = null;
  currentText = '';
  vscode.postMessage({ type: 'send', text });
}

window.addEventListener('message', (e) => {
  const { type, data } = e.data;
  if (type === 'chunk') {
    if (!currentBubble) {
      currentBubble = addMsg('assistant', '');
      currentText = '';
    }
    currentText += data;
    renderMarkdown(currentBubble, currentText);
    chat.scrollTop = chat.scrollHeight;
  } else if (type === 'done') {
    if (currentBubble && !currentText) {
      currentBubble.textContent = '（无回复）';
    }
    currentBubble = null;
    btnSend.disabled = false;
  } else if (type === 'error') {
    addMsg('error', data);
    currentBubble = null;
    btnSend.disabled = false;
  } else if (type === 'tool') {
    addMsg('tool', '调用 ' + data.name + '(' + JSON.stringify(data.args) + ')');
  } else if (type === 'cleared') {
    chat.innerHTML = '';
  }
});

addMsg('assistant', '你好，我是小智。可以让我帮你写 HX 代码、改文件、运行程序。\n\n试试：\n· 写一个贪吃蛇\n· 帮我看看当前代码有什么问题\n· 用 UI 组件做一个登录界面');
</script>
</body>
</html>`;
    }

    dispose() {
        AgentPanel.currentPanel = undefined;
        this.panel.dispose();
        while (this.disposables.length) {
            const d = this.disposables.pop();
            if (d) {
                d.dispose();
            }
        }
    }
}
