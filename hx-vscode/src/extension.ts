import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { runFile } from './runner';
import { AgentPanel } from './agent/panel';
import { ChatChannel } from './agent/chat';
import { DesignerPanel } from './designer/panel';
import { HxCompletionProvider, HxHoverProvider } from './providers';
import { DiagnosticsManager } from './diagnostics';
import { HxDocumentSymbolProvider } from './symbols';
import { ApiDocsProvider } from './api-docs-view';

let agentPanel: AgentPanel | undefined;
let chatChannel: ChatChannel | undefined;
let designerPanel: DesignerPanel | undefined;

/**
 * 查找 hx.py 的绝对路径
 * 优先级：配置 > 工作区根目录 > 扩展内置 python 目录
 */
export function findInterpreter(context: vscode.ExtensionContext): string | undefined {
    const cfg = vscode.workspace.getConfiguration('hx');
    const configured = cfg.get<string>('interpreterPath');
    if (configured && fs.existsSync(configured)) {
        return configured;
    }
    const folders = vscode.workspace.workspaceFolders;
    if (folders) {
        for (const folder of folders) {
            const p = path.join(folder.uri.fsPath, 'hx.py');
            if (fs.existsSync(p)) {
                return p;
            }
        }
    }
    const bundled = path.join(context.extensionPath, 'python', 'hx.py');
    if (fs.existsSync(bundled)) {
        return bundled;
    }
    return undefined;
}

export async function getApiKey(context: vscode.ExtensionContext): Promise<string> {
    const stored = await context.secrets.get('hx.ai.apiKey');
    if (stored) {
        return stored;
    }
    const cfg = vscode.workspace.getConfiguration('hx');
    return cfg.get<string>('ai.apiKey') || '';
}

export function getApiConfig() {
    const cfg = vscode.workspace.getConfiguration('hx');
    return {
        baseUrl: cfg.get<string>('ai.baseUrl') || 'https://api.deepseek.com/v1',
        model: cfg.get<string>('ai.model') || 'deepseek-chat',
    };
}

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand('hx.run', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('没有打开的编辑器');
                return;
            }
            const py = findInterpreter(context);
            if (!py) {
                vscode.window.showErrorMessage('找不到 hx.py。请在设置里配置 hx.interpreterPath');
                return;
            }
            runFile(editor.document.uri.fsPath, py);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('hx.openAgent', () => {
            // 优先 Webview 面板（体验最好）
            try {
                if (agentPanel) {
                    agentPanel.reveal();
                    return;
                }
                agentPanel = new AgentPanel(context);
                agentPanel.onDidDispose(() => { agentPanel = undefined; });
                agentPanel.reveal();
            } catch (e: any) {
                // Webview 不可用（CodeGeeX 等衍生版），降级到 OutputChannel
                vscode.window.showWarningMessage(
                    'Webview 不可用，已切换到文字版小智。原因：' + (e.message || String(e))
                );
                vscode.commands.executeCommand('hx.openAgentText');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('hx.openAgentText', async () => {
            // 文字版小智：OutputChannel + InputBox
            if (!chatChannel) {
                chatChannel = new ChatChannel(context);
                context.subscriptions.push({ dispose: () => chatChannel && chatChannel.dispose() });
            }
            await chatChannel.start();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('hx.openDesigner', () => {
            if (designerPanel) {
                designerPanel.reveal();
                return;
            }
            designerPanel = new DesignerPanel(context);
            designerPanel.onDidDispose(() => { designerPanel = undefined; });
            designerPanel.reveal();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('hx.setApiKey', async () => {
            const key = await vscode.window.showInputBox({
                title: 'HX 小智 API Key',
                prompt: '输入 OpenAI 兼容接口的 API Key（保存到 VS Code 加密存储）',
                password: true,
                ignoreFocusOut: true,
            });
            if (key === undefined) {
                return;
            }
            if (key === '') {
                await context.secrets.delete('hx.ai.apiKey');
                vscode.window.showInformationMessage('已清除 API Key');
                return;
            }
            await context.secrets.store('hx.ai.apiKey', key);
            vscode.window.showInformationMessage('API Key 已保存');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('hx.cheatsheet', async () => {
            const doc = await vscode.workspace.openTextDocument({
                language: 'markdown',
                content: buildCheatsheet(),
            });
            await vscode.window.showTextDocument(doc, { preview: true });
        })
    );

    const selector: vscode.DocumentSelector = { scheme: 'file', language: 'hx' };
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(selector, new HxCompletionProvider(), '.')
    );
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(selector, new HxHoverProvider())
    );
    context.subscriptions.push(
        vscode.languages.registerDocumentSymbolProvider(selector, new HxDocumentSymbolProvider())
    );

    // 实时语法诊断
    const diagMgr = new DiagnosticsManager(context);
    for (const d of diagMgr.register()) {
        context.subscriptions.push(d);
    }
    context.subscriptions.push({ dispose: () => diagMgr.dispose() });

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            ApiDocsProvider.viewType,
            new ApiDocsProvider(context.extensionUri)
        )
    );

    const statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusItem.text = '$(sparkle) 小智';
    statusItem.tooltip = '打开 HX 小智 Agent';
    statusItem.command = 'hx.openAgent';
    statusItem.show();
    context.subscriptions.push(statusItem);
}

export function deactivate() {}

function buildCheatsheet(): string {
    const BT = String.fromCharCode(96);
    const F = BT + BT + BT;
    const L: string[] = [];
    const p = (s: string) => L.push(s);

    p('# HX 语言速查');
    p('');

    p('## 变量');
    p('直接赋值，自动判断类型：');
    p('');
    p(F + 'hx');
    p('x = 10;');
    p('s = "hi";');
    p('arr = [1, 2, 3];');
    p('d = {name: "hx", ver: 3};');
    p(F);
    p('');

    p('## 函数（C 风格）');
    p('');
    p(F + 'hx');
    p('add(a, b) { return a + b; }');
    p('fib(n) {');
    p('  if (n < 2) { return n; }');
    p('  return fib(n - 1) + fib(n - 2);');
    p('}');
    p(F);
    p('');

    p('## 控制流');
    p('');
    p(F + 'hx');
    p('if (x > 5) { print("big"); }');
    p('else if (x > 0) { print("small"); }');
    p('else { print("zero"); }');
    p('');
    p('for (i = 0; i < n; i += 1) { print(i); }');
    p('while (i < 10) { i += 1; }');
    p('');
    p('try { print(undefined); } catch (e) { print("err:", e); }');
    p(F);
    p('');

    p('## 输入输出');
    p('');
    p(F + 'hx');
    p('print("hi", 1);');
    p('input("提示");');
    p('scanf("%d %d", a, b);');
    p('help();');
    p(F);
    p('');

    p('## 内置函数');
    p('');
    p('- 类型：' + BT + 'type' + BT);
    p('- 数组：' + BT + 'len push min max abs range' + BT);
    p('- 字典：' + BT + 'keys items has set' + BT);
    p('- 字符串：' + BT + 'upper lower trim split join' + BT);
    p('- 转换：' + BT + 'str num' + BT);
    p('- 数学：' + BT + 'sqrt sin cos tan floor ceil round random PI' + BT);
    p('');

    p('## 图形');
    p('');
    p(F + 'hx');
    p('gwin(600, 400, "画板");');
    p('grect(0, 0, 600, 400, "white", "lightcyan");');
    p('gcircle(300, 200, 80, "orange", "gold");');
    p('gline(50, 350, 550, 350, "blue", 3);');
    p('gtext(250, 50, "Hello!", "navy");');
    p('gsleep(2000);');
    p(F);
    p('');

    p('## 事件');
    p('');
    p(F + 'hx');
    p('k = gwaitkey(3000);');
    p('p = gwaitclick(3000);');
    p('');
    p('on_key(key) { print(key); }');
    p('gkeydown(on_key);');
    p(F);
    p('');

    p('## UI 组件');
    p('');
    p('统一签名 ' + BT + '(id, x, y, 宽, 高, ...)' + BT + '：');
    p('');
    p('- 基础：' + BT + 'uiheading uilabel uibtn' + BT);
    p('- 输入：' + BT + 'uiinput uitext uicheck uiradio uicombo uilist uirange' + BT);
    p('- 显示：' + BT + 'uiprogress uiimage uitable' + BT);
    p('- 布局：' + BT + 'uipanel uiseparator uitabs' + BT);
    p('- 交互：' + BT + 'uion(id, "click", fn)' + BT + ' / ' + BT + 'uiget' + BT + ' / ' + BT + 'uiset' + BT + ' / ' + BT + 'uirun()' + BT);
    p('');

    p('## 网络与后台');
    p('');
    p(F + 'hx');
    p('s = http_get("https://example.com");');
    p('http_download("https://example.com/a.zip", "a.zip");');
    p('');
    p('on_done(r) { print("收到", r); }');
    p('bg_run(http_get, "https://example.com", on_done);');
    p(F);
    p('');

    p('## 压缩与哈希');
    p('');
    p(F + 'hx');
    p('md5("file.txt");');
    p('sha256("file.txt");');
    p('zipinfo("a.zip");');
    p('unzip("a.zip", "out");');
    p(F);
    p('');

    p('## 文件');
    p('');
    p(F + 'hx');
    p('writefile("a.txt", "hello");');
    p('s = readfile("a.txt");');
    p('exists("a.txt");');
    p('files(".");');
    p('openfile("a.txt");');
    p('openurl("https://example.com");');
    p('runapp("notepad.exe");');
    p(F);

    return L.join('\n');
}
