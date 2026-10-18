import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

let currentTerminal: vscode.Terminal | undefined;

/**
 * 在 VS Code 集成终端里运行 HX 文件
 * 用终端而不是 output channel，因为 HX 支持 input()/scanf() 交互
 */
export function runFile(filePath: string, interpreterPath: string) {
    const cfg = vscode.workspace.getConfiguration('hx');
    const python = cfg.get<string>('pythonPath') || 'python';
    const workDir = path.dirname(filePath);
    const fileName = path.basename(filePath);

    // 复用已有终端，没有就新建
    let term = currentTerminal;
    if (!term || term.exitStatus !== undefined) {
        term = vscode.window.createTerminal({
            name: 'HX',
            cwd: workDir,
        });
        currentTerminal = term;
    } else {
        term.dispose();
        term = vscode.window.createTerminal({
            name: 'HX',
            cwd: workDir,
        });
        currentTerminal = term;
    }

    term.show();

    // 引号处理：只给含空格的路径加引号，命令本身不加
    // 反例（PowerShell 会报"意外的标记"）："python" "c:\a\hx.py" "b.hxg"
    // 正例：python "c:\a b\hx.py" b.hxg
    const q = (s: string) => (/\s/.test(s) ? '"' + s + '"' : s);
    let cmd = q(python) + ' ' + q(interpreterPath) + ' ' + q(fileName);
    // PowerShell：命令本身含空格时需要用 & 调用运算符
    if (process.platform === 'win32' && /\s/.test(python)) {
        cmd = '& ' + cmd;
    }
    term.sendText(cmd, true);
}

/**
 * 无终端运行（捕获输出），用于 UI 画板预览
 */
export function runFileCapture(filePath: string, interpreterPath: string): Promise<{ code: number; stdout: string; stderr: string }> {
    return new Promise((resolve) => {
        const cfg = vscode.workspace.getConfiguration('hx');
        const python = cfg.get<string>('pythonPath') || 'python';
        cp.execFile(python, [interpreterPath, filePath], {
            cwd: path.dirname(filePath),
            timeout: 60000,
            maxBuffer: 10 * 1024 * 1024,
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        }, (err, stdout, stderr) => {
            resolve({
                code: err ? (typeof (err as any).code === 'number' ? (err as any).code : 1) : 0,
                stdout: stdout || '',
                stderr: stderr || '',
            });
        });
    });
}
