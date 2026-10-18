import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

/**
 * 用 hx_check.py 做语法检查，生成红色波浪线
 * 文档变化后 400ms 防抖，避免频繁调用
 */
export class DiagnosticsManager {
    private collection: vscode.DiagnosticCollection;
    private timers = new Map<string, NodeJS.Timeout>();
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.collection = vscode.languages.createDiagnosticCollection('hx');
    }

    register(): vscode.Disposable[] {
        const disposables: vscode.Disposable[] = [
            this.collection,
            vscode.workspace.onDidChangeTextDocument((e) => {
                if (e.document.languageId === 'hx') {
                    this.schedule(e.document);
                }
            }),
            vscode.workspace.onDidOpenTextDocument((doc) => {
                if (doc.languageId === 'hx') {
                    this.schedule(doc);
                }
            }),
            vscode.workspace.onDidCloseTextDocument((doc) => {
                this.collection.delete(doc.uri);
                const t = this.timers.get(doc.uri.toString());
                if (t) {
                    clearTimeout(t);
                    this.timers.delete(doc.uri.toString());
                }
            }),
        ];
        // 打开时已有文档
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.languageId === 'hx') {
                this.schedule(doc);
            }
        }
        return disposables;
    }

    private schedule(doc: vscode.TextDocument) {
        const key = doc.uri.toString();
        const old = this.timers.get(key);
        if (old) {
            clearTimeout(old);
        }
        const timer = setTimeout(() => {
            this.timers.delete(key);
            this.check(doc);
        }, 400);
        this.timers.set(key, timer);
    }

    private check(doc: vscode.TextDocument) {
        const py = path.join(this.context.extensionPath, 'python', 'hx_check.py');
        const cfg = vscode.workspace.getConfiguration('hx');
        const python = cfg.get<string>('pythonPath') || 'python';
        const src = doc.getText();

        const proc = cp.spawn(python, [py], {
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        });

        let stdout = '';
        let stderr = '';
        proc.stdout.on('data', (c) => { stdout += c.toString('utf-8'); });
        proc.stderr.on('data', (c) => { stderr += c.toString('utf-8'); });
        proc.on('error', (err) => {
            // python 找不到，静默失败（不要每次都弹窗）
        });
        proc.on('close', () => {
            if (!stdout.trim()) {
                this.collection.delete(doc.uri);
                return;
            }
            try {
                const result = JSON.parse(stdout);
                const errors = result.errors || [];
                const diags: vscode.Diagnostic[] = [];
                for (const e of errors) {
                    const line = Math.max(0, (e.line || 1) - 1);
                    const col = Math.max(0, (e.col || 1) - 1);
                    const endLine = Math.max(line, (e.endLine || e.line || 1) - 1);
                    const endCol = Math.max(col + 1, (e.endCol || e.col || 1));
                    // 保护：行号不能超出文档
                    const safeLine = Math.min(line, doc.lineCount - 1);
                    const lineText = doc.lineAt(safeLine).text;
                    const safeCol = Math.min(col, Math.max(0, lineText.length));
                    const range = new vscode.Range(
                        new vscode.Position(safeLine, safeCol),
                        new vscode.Position(safeLine, Math.max(safeCol + 1, Math.min(lineText.length, safeCol + 20)))
                    );
                    const d = new vscode.Diagnostic(
                        range,
                        e.message || '语法错误',
                        e.severity === 'warning' ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error
                    );
                    d.source = 'hx';
                    diags.push(d);
                }
                this.collection.set(doc.uri, diags);
            } catch {
                // JSON 解析失败，忽略
            }
        });
        proc.stdin.write(src);
        proc.stdin.end();
    }

    dispose() {
        for (const t of this.timers.values()) {
            clearTimeout(t);
        }
        this.timers.clear();
        this.collection.dispose();
    }
}
