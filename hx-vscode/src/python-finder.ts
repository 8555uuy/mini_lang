import * as fs from 'fs';
import * as path from 'path';
import * as cp from 'child_process';
import * as os from 'os';

/**
 * 自动探测 Python 解释器路径
 * 顺序：配置 > 常见安装位置 > PATH 里的 python
 */

const CACHE = { path: '' as string, ts: 0 };
const CACHE_TTL = 60000;

export function findPython(configuredPath: string): string {
    // 1. 用户配置的路径（如果是绝对路径且存在，直接用）
    if (configuredPath && path.isAbsolute(configuredPath) && fs.existsSync(configuredPath)) {
        return configuredPath;
    }

    // 2. 缓存
    const now = Date.now();
    if (CACHE.path && (now - CACHE.ts) < CACHE_TTL) {
        return CACHE.path;
    }

    // 3. 扫常见位置
    const candidates: string[] = [];

    // 3.1 当前环境 PATH 里能不能找到
    const pathDirs = (process.env.PATH || '').split(path.delimiter);
    for (const dir of pathDirs) {
        if (!dir) continue;
        for (const name of ['python.exe', 'python3.exe', 'py.exe']) {
            const p = path.join(dir, name);
            if (fs.existsSync(p)) {
                candidates.push(p);
            }
        }
    }

    // 3.2 Windows 常见安装路径
    if (process.platform === 'win32') {
        const localAppData = process.env.LOCALAPPDATA || '';
        const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
        const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
        const userProfile = process.env.USERPROFILE || '';

        // python.org 安装
        const dirs = [
            path.join(localAppData, 'Programs', 'Python'),
            path.join(programFiles, 'Python'),
            path.join(programFilesX86, 'Python'),
            path.join(localAppData, 'Microsoft', 'WindowsApps'),
            'C:\\Python',
        ];
        for (const base of dirs) {
            if (!fs.existsSync(base)) continue;
            try {
                const entries = fs.readdirSync(base);
                for (const e of entries) {
                    if (e.toLowerCase().startsWith('python')) {
                        const exe = path.join(base, e, 'python.exe');
                        if (fs.existsSync(exe)) {
                            candidates.push(exe);
                        }
                    }
                }
            } catch {}
        }

        // 已知用户路径（当前机器）
        const known = [
            path.join(userProfile, 'AppData', 'Local', 'Python', 'pythoncore-3.14-64', 'python.exe'),
            path.join(userProfile, 'AppData', 'Local', 'Python', 'pythoncore-3.13-64', 'python.exe'),
            path.join(userProfile, 'AppData', 'Local', 'Python', 'pythoncore-3.12-64', 'python.exe'),
            path.join(localAppData, 'Python', 'pythoncore-3.14-64', 'python.exe'),
            path.join(localAppData, 'Python', 'pythoncore-3.13-64', 'python.exe'),
            path.join(localAppData, 'Python', 'pythoncore-3.12-64', 'python.exe'),
        ];
        for (const k of known) {
            if (fs.existsSync(k)) candidates.push(k);
        }

        // 扫 LOCALAPPDATA\\Python 和 LOCALAPPDATA\\Programs\\Python 下所有 pythoncore-* 和 Python*
        for (const base of [path.join(localAppData, 'Python'), path.join(localAppData, 'Programs', 'Python')]) {
            if (!fs.existsSync(base)) continue;
            try {
                for (const e of fs.readdirSync(base)) {
                    const exe = path.join(base, e, 'python.exe');
                    if (fs.existsSync(exe)) candidates.push(exe);
                }
            } catch {}
        }

        // 扫 py launcher 安装位置（注册表方式太麻烦，直接找已知路径）
        const pyLauncher = path.join(process.env.SystemRoot || 'C:\\Windows', 'py.exe');
        if (fs.existsSync(pyLauncher)) candidates.push(pyLauncher);
    } else {
        // macOS / Linux
        const unixPaths = [
            '/usr/bin/python3',
            '/usr/local/bin/python3',
            '/opt/homebrew/bin/python3',
            path.join(os.homedir(), '.pyenv', 'shims', 'python3'),
        ];
        for (const p of unixPaths) {
            if (fs.existsSync(p)) candidates.push(p);
        }
    }

    // 4. 逐个验证能否运行（能跑 --version 才算）
    for (const c of candidates) {
        if (testPython(c)) {
            CACHE.path = c;
            CACHE.ts = now;
            return c;
        }
    }

    // 5. 兜底：用配置值（可能就是 'python'）
    return configuredPath || 'python';
}

function testPython(exe: string): boolean {
    try {
        const r = cp.spawnSync(exe, ['--version'], {
            timeout: 3000,
            encoding: 'utf-8',
            windowsHide: true,
        });
        if (r.error) return false;
        const out = (r.stdout || '') + (r.stderr || '');
        return /Python \d+\.\d+/.test(out);
    } catch {
        return false;
    }
}

export function clearPythonCache() {
    CACHE.path = '';
    CACHE.ts = 0;
}
