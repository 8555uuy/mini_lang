import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

let agentPanel: any = undefined;
let chatChannel: any = undefined;
let designerPanel: any = undefined;

/**
 * 找到 hx.py 的绝对路径
 */
export function findInterpreter(context: vscode.ExtensionContext): string | undefined {
    try {
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
    } catch (e) {
        // ignore
    }
    return undefined;
}

export async function getApiKey(context: vscode.ExtensionContext): Promise<string> {
    try {
        const stored = await context.secrets.get('hx.ai.apiKey');
        if (stored) {
            return stored;
        }
    } catch (e) {
        // 某些衍生版可能不支持 secrets
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
    const out = vscode.window.createOutputChannel('HX');
    context.subscriptions.push(out);
    out.appendLine('HX 扩展激活中…');

    const safe = (name: string, fn: () => void) => {
        try {
            fn();
        } catch (e: any) {
            out.appendLine('❌ ' + name + ' 失败：' + (e.message || String(e)));
        }
    };

    // ========== 运行 ==========
    safe('registerCommand hx.run', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.run', () => {
                const editor = vscode.window.activeTextEditor;
                if (!editor) {
                    vscode.window.showWarningMessage('没有打开的编辑器');
                    return;
                }
                const py = findInterpreter(context);
                if (!py) {
                    vscode.window.showErrorMessage('找不到 hx.py');
                    return;
                }
                const runner = require('./runner');
                runner.runFile(editor.document.uri.fsPath, py);
            })
        );
    });

    // ========== 小智（文字版，最稳） ==========
    safe('registerCommand hx.openAgentText', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.openAgentText', async () => {
                try {
                    const chatMod = require('./agent/chat');
                    if (!chatChannel) {
                        chatChannel = new chatMod.ChatChannel(context);
                        context.subscriptions.push({ dispose: () => chatChannel && chatChannel.dispose() });
                    }
                    await chatChannel.start();
                } catch (e: any) {
                    vscode.window.showErrorMessage('小智启动失败：' + (e.message || String(e)));
                }
            })
        );
    });

    // ========== 小智（Webview 版，可用则用） ==========
    safe('registerCommand hx.openAgent', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.openAgent', () => {
                try {
                    if (agentPanel) {
                        agentPanel.reveal();
                        return;
                    }
                    const panelMod = require('./agent/panel');
                    agentPanel = new panelMod.AgentPanel(context);
                    agentPanel.onDidDispose(() => { agentPanel = undefined; });
                    agentPanel.reveal();
                } catch (e: any) {
                    vscode.window.showWarningMessage(
                        'Webview 不可用，切换到文字版小智。'
                    );
                    vscode.commands.executeCommand('hx.openAgentText');
                }
            })
        );
    });

    // ========== UI 画板 ==========
    safe('registerCommand hx.openDesigner', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.openDesigner', () => {
                try {
                    if (designerPanel) {
                        designerPanel.reveal();
                        return;
                    }
                    const mod = require('./designer/panel');
                    designerPanel = new mod.DesignerPanel(context);
                    designerPanel.onDidDispose(() => { designerPanel = undefined; });
                    designerPanel.reveal();
                } catch (e: any) {
                    vscode.window.showErrorMessage('UI 画板启动失败：' + (e.message || String(e)));
                }
            })
        );
    });

    // ========== API Key ==========
    safe('registerCommand hx.setApiKey', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.setApiKey', async () => {
                const key = await vscode.window.showInputBox({
                    title: 'HX 小智 API Key',
                    prompt: '输入 OpenAI 兼容接口的 API Key',
                    password: true,
                    ignoreFocusOut: true,
                });
                if (key === undefined) {
                    return;
                }
                try {
                    if (key === '') {
                        await context.secrets.delete('hx.ai.apiKey');
                        vscode.window.showInformationMessage('已清除');
                    } else {
                        await context.secrets.store('hx.ai.apiKey', key);
                        vscode.window.showInformationMessage('已保存');
                    }
                } catch (e: any) {
                    vscode.window.showErrorMessage('保存失败：' + (e.message || String(e)));
                }
            })
        );
    });

    // ========== 语法速查（Markdown） ==========
    safe('registerCommand hx.cheatsheet', () => {
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.cheatsheet', async () => {
                try {
                    const md = require('./cheatsheet');
                    const doc = await vscode.workspace.openTextDocument({
                        language: 'markdown',
                        content: md.buildCheatsheet(),
                    });
                    await vscode.window.showTextDocument(doc, { preview: true });
                } catch (e: any) {
                    vscode.window.showErrorMessage('速查打开失败：' + (e.message || String(e)));
                }
            })
        );
    });

    // ========== API 速查（TreeView） ==========
    safe('registerTreeDataProvider hx.apiDocs', () => {
        const treeMod = require('./api-tree');
        const provider = new treeMod.ApiTreeProvider();
        const view = vscode.window.createTreeView('hx.apiDocs', {
            treeDataProvider: provider,
            showCollapseAll: true,
        });
        context.subscriptions.push(view);

        // 插入示例命令
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.insertApiExample', async (entry: any) => {
                if (!entry || !entry.example) {
                    return;
                }
                const editor = vscode.window.activeTextEditor;
                if (!editor || editor.document.languageId !== 'hx') {
                    // 没打开 HX 文件，创建新文件并插入
                    const doc = await vscode.workspace.openTextDocument({
                        language: 'hx',
                        content: '// ' + entry.sig + '\n' + entry.example + '\n',
                    });
                    await vscode.window.showTextDocument(doc, { preview: false });
                    return;
                }
                await editor.edit((b) => b.insert(editor.selection.active, entry.example));
            })
        );

        // 搜索命令
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.searchApi', async () => {
                const kw = await vscode.window.showInputBox({
                    title: '搜索 HX API',
                    prompt: '输入函数名或关键词（留空清空过滤）',
                });
                if (kw === undefined) {
                    return;
                }
                provider.setFilter(kw);
            })
        );

        // 清空搜索
        context.subscriptions.push(
            vscode.commands.registerCommand('hx.clearApiFilter', () => {
                provider.setFilter('');
            })
        );

        out.appendLine('✅ API 速查 TreeView 已注册');
    });

    // ========== 补全 / 悬停 / 符号 ==========
    safe('registerCompletionItemProvider', () => {
        const p = require('./providers');
        const selector: vscode.DocumentSelector = { scheme: 'file', language: 'hx' };
        context.subscriptions.push(
            vscode.languages.registerCompletionItemProvider(selector, new p.HxCompletionProvider(), '.')
        );
    });

    safe('registerHoverProvider', () => {
        const p = require('./providers');
        const selector: vscode.DocumentSelector = { scheme: 'file', language: 'hx' };
        context.subscriptions.push(
            vscode.languages.registerHoverProvider(selector, new p.HxHoverProvider())
        );
    });

    safe('registerDocumentSymbolProvider', () => {
        const s = require('./symbols');
        const selector: vscode.DocumentSelector = { scheme: 'file', language: 'hx' };
        context.subscriptions.push(
            vscode.languages.registerDocumentSymbolProvider(selector, new s.HxDocumentSymbolProvider())
        );
    });

    // ========== 实时诊断 ==========
    safe('DiagnosticsManager', () => {
        const d = require('./diagnostics');
        const mgr = new d.DiagnosticsManager(context);
        for (const disp of mgr.register()) {
            context.subscriptions.push(disp);
        }
        context.subscriptions.push({ dispose: () => mgr.dispose() });
    });

    // ========== 状态栏 ==========
    safe('createStatusBarItem', () => {
        const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        item.text = '$(sparkle) 小智';
        item.tooltip = '打开 HX 小智';
        item.command = 'hx.openAgentText';
        item.show();
        context.subscriptions.push(item);
    });

    // ========== 诊断命令 ==========
    context.subscriptions.push(
        vscode.commands.registerCommand('hx.diagnose', async () => {
            out.show(true);
            out.appendLine('');
            out.appendLine('════════ 扩展诊断 ════════');
            out.appendLine('扩展路径：' + context.extensionPath);
            out.appendLine('VS Code：' + vscode.version);
            out.appendLine('Node：' + process.version);
            out.appendLine('');
            out.appendLine('── 已注册的命令 ──');
            const cmds = await vscode.commands.getCommands(true);
            for (const c of cmds) {
                if (c.startsWith('hx.')) {
                    out.appendLine('  ' + c);
                }
            }
            out.appendLine('');
            out.appendLine('── 文件完整性 ──');
            const files = [
                'python/hx.py',
                'python/hx_check.py',
                'syntaxes/hx.tmLanguage.json',
                'snippets/hx.json',
                'out/extension.js',
                'out/providers.js',
                'out/api-tree.js',
                'out/agent/chat.js',
            ];
            for (const f of files) {
                const abs = path.join(context.extensionPath, f);
                out.appendLine('  ' + (fs.existsSync(abs) ? '✅' : '❌') + ' ' + f);
            }
            out.appendLine('');
            out.appendLine('── API 可用性 ──');
            const checks: [string, boolean][] = [
                ['registerWebviewViewProvider', typeof (vscode.window as any).registerWebviewViewProvider === 'function'],
                ['createWebviewPanel', typeof (vscode.window as any).createWebviewPanel === 'function'],
                ['createTreeView', typeof (vscode.window as any).createTreeView === 'function'],
                ['secrets', typeof (context.secrets as any) !== 'undefined'],
                ['registerCompletionItemProvider', typeof vscode.languages.registerCompletionItemProvider === 'function'],
            ];
            for (const [name, ok] of checks) {
                out.appendLine('  ' + (ok ? '✅' : '❌') + ' ' + name);
            }
            out.appendLine('');
            out.appendLine('诊断完成。');
        })
    );

    out.appendLine('✅ 激活完成');
}

export function deactivate() {}
