import * as vscode from 'vscode';
import { getApiConfig } from './extension';
import { clearPythonCache } from './python-finder';

/**
 * 设置面板
 * - Webview 表单（可视化）
 * - 不可用时自动降级到 QuickPick 向导
 */

interface Config {
    baseUrl: string;
    model: string;
    apiKey: string;
    pythonPath: string;
    interpreterPath: string;
}

export async function openSettings(context: vscode.ExtensionContext) {
    const cfg = vscode.workspace.getConfiguration('hx');
    const apiCfg = getApiConfig();
    let apiKey = '';
    try {
        apiKey = (await context.secrets.get('hx.ai.apiKey')) || '';
    } catch {}
    if (!apiKey) {
        apiKey = cfg.get<string>('ai.apiKey') || '';
    }

    const current: Config = {
        baseUrl: apiCfg.baseUrl,
        model: apiCfg.model,
        apiKey,
        pythonPath: cfg.get<string>('pythonPath') || 'python',
        interpreterPath: cfg.get<string>('interpreterPath') || '',
    };

    try {
        await openWebviewSettings(context, current);
    } catch (e) {
        vscode.window.showWarningMessage('Webview 不可用，切换到向导模式');
        await openQuickPickSettings(context, current);
    }
}

/** Webview 版设置面板 */
async function openWebviewSettings(context: vscode.ExtensionContext, current: Config) {
    const panel = vscode.window.createWebviewPanel(
        'hxSettings',
        'HX 设置',
        vscode.ViewColumn.Active,
        { enableScripts: true, retainContextWhenHidden: true }
    );
    panel.webview.html = getSettingsHtml(current, context);

    // 接收表单提交
    panel.webview.onDidReceiveMessage(async (msg) => {
        if (msg.type === 'save') {
            const data = msg.data as Config;
            const cfg = vscode.workspace.getConfiguration('hx');
            await cfg.update('ai.baseUrl', data.baseUrl, vscode.ConfigurationTarget.Global);
            await cfg.update('ai.model', data.model, vscode.ConfigurationTarget.Global);
            await cfg.update('pythonPath', data.pythonPath, vscode.ConfigurationTarget.Global);
            await cfg.update('interpreterPath', data.interpreterPath, vscode.ConfigurationTarget.Global);
            try {
                if (data.apiKey) {
                    await context.secrets.store('hx.ai.apiKey', data.apiKey);
                } else {
                    await context.secrets.delete('hx.ai.apiKey');
                }
            } catch (e: any) {
                vscode.window.showWarningMessage('API Key 保存失败（该编辑器可能不支持 SecretStorage）：' + (e.message || String(e)));
            }
            clearPythonCache();
            vscode.window.showInformationMessage('HX 设置已保存');
            panel.dispose();
        } else if (msg.type === 'test') {
            // 测试 Python
            const result = testPythonPath(msg.path);
            panel.webview.postMessage({ type: 'testResult', ok: result.ok, message: result.message });
        } else if (msg.type === 'cancel') {
            panel.dispose();
        }
    });
}

/** QuickPick 版设置向导（备用） */
async function openQuickPickSettings(context: vscode.ExtensionContext, current: Config) {
    const cfg = vscode.workspace.getConfiguration('hx');

    const baseUrl = await vscode.window.showInputBox({
        title: '① API 地址',
        prompt: 'OpenAI 兼容接口的 Base URL',
        value: current.baseUrl,
        placeHolder: 'https://api.deepseek.com/v1',
        ignoreFocusOut: true,
    });
    if (baseUrl === undefined) return;

    const model = await vscode.window.showInputBox({
        title: '② 模型名',
        prompt: '使用的模型',
        value: current.model,
        placeHolder: 'deepseek-chat',
        ignoreFocusOut: true,
    });
    if (model === undefined) return;

    const apiKey = await vscode.window.showInputBox({
        title: '③ API Key',
        prompt: '留空则不修改',
        password: true,
        placeHolder: current.apiKey ? '（已设置，留空保持不变）' : '输入 API Key',
        ignoreFocusOut: true,
    });
    if (apiKey === undefined) return;

    const pythonPath = await vscode.window.showInputBox({
        title: '④ Python 路径',
        prompt: '运行 HX 解释器的 python 路径（可留空自动探测）',
        value: current.pythonPath,
        placeHolder: 'python 或 C:\\Python\\python.exe',
        ignoreFocusOut: true,
    });
    if (pythonPath === undefined) return;

    await cfg.update('ai.baseUrl', baseUrl.trim(), vscode.ConfigurationTarget.Global);
    await cfg.update('ai.model', model.trim(), vscode.ConfigurationTarget.Global);
    await cfg.update('pythonPath', pythonPath.trim(), vscode.ConfigurationTarget.Global);
    if (apiKey.trim()) {
        try {
            await context.secrets.store('hx.ai.apiKey', apiKey.trim());
        } catch {}
    }
    clearPythonCache();
    vscode.window.showInformationMessage('HX 设置已保存');
}

function testPythonPath(p: string): { ok: boolean; message: string } {
    try {
        const cp = require('child_process');
        const path = p && p.trim() ? p.trim() : 'python';
        const r = cp.spawnSync(path, ['--version'], { timeout: 3000, encoding: 'utf-8', windowsHide: true });
        if (r.error) {
            return { ok: false, message: '无法执行：' + (r.error.message || String(r.error)) };
        }
        const out = ((r.stdout || '') + (r.stderr || '')).trim();
        if (/Python \d+\.\d+/.test(out)) {
            return { ok: true, message: out };
        }
        return { ok: false, message: '输出不是 Python 版本：' + out.slice(0, 100) };
    } catch (e: any) {
        return { ok: false, message: e.message || String(e) };
    }
}

function getSettingsHtml(current: Config, context: vscode.ExtensionContext): string {
    const nonce = String(Date.now());
    const data = JSON.stringify(current);
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
  padding: 24px;
  max-width: 720px;
  margin: 0 auto;
}
h1 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}
.subtitle {
  color: var(--vscode-descriptionForeground);
  font-size: 12px;
  margin-bottom: 24px;
}
.section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid var(--vscode-panel-border);
  border-radius: 6px;
  background: var(--vscode-sideBar-background);
}
.section h2 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section h2 .badge {
  background: var(--vscode-badge-background);
  color: var(--vscode-badge-foreground);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 400;
}
.field {
  margin-bottom: 14px;
}
.field:last-child { margin-bottom: 0; }
.field label {
  display: block;
  font-size: 12px;
  color: var(--vscode-descriptionForeground);
  margin-bottom: 4px;
}
.field .hint {
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
  opacity: 0.8;
  margin-top: 3px;
}
.field input {
  width: 100%;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, var(--vscode-panel-border));
  border-radius: 4px;
  padding: 7px 10px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
}
.field input:focus { border-color: var(--vscode-focusBorder); }
.presets {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.preset {
  background: transparent;
  color: var(--vscode-textLink-foreground);
  border: 1px solid var(--vscode-panel-border);
  border-radius: 3px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
.preset:hover { background: var(--vscode-toolbar-hoverBackground); }
.test-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}
.test-btn {
  background: transparent;
  color: var(--vscode-textLink-foreground);
  border: 1px solid var(--vscode-panel-border);
  border-radius: 3px;
  padding: 4px 12px;
  font-size: 11px;
  cursor: pointer;
}
.test-btn:hover { background: var(--vscode-toolbar-hoverBackground); }
.test-result {
  font-size: 11px;
  font-family: var(--vscode-editor-font-family);
}
.test-result.ok { color: #4ec9b0; }
.test-result.err { color: #f14c4c; }
.actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 1px solid var(--vscode-panel-border);
  margin-top: 24px;
  padding-top: 16px;
}
.btn {
  border: none;
  border-radius: 4px;
  padding: 8px 20px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}
.btn.primary {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
}
.btn.primary:hover { background: var(--vscode-button-hoverBackground); }
.btn.secondary {
  background: transparent;
  color: var(--vscode-foreground);
  border: 1px solid var(--vscode-panel-border);
}
.btn.secondary:hover { background: var(--vscode-toolbar-hoverBackground); }
</style>
</head>
<body>
<h1>HX 设置</h1>
<div class="subtitle">配置小智 AI 和 Python 解释器</div>

<div class="section">
  <h2>小智 AI <span class="badge">OpenAI 兼容接口</span></h2>
  <div class="field">
    <label>API 地址</label>
    <input id="baseUrl" type="text" value="" placeholder="https://api.deepseek.com/v1">
    <div class="presets">
      <button class="preset" data-url="https://api.deepseek.com/v1" data-model="deepseek-chat">DeepSeek</button>
      <button class="preset" data-url="https://api.moonshot.cn/v1" data-model="moonshot-v1-8k">Kimi</button>
      <button class="preset" data-url="https://dashscope.aliyuncs.com/compatible-mode/v1" data-model="qwen-plus">通义千问</button>
      <button class="preset" data-url="https://open.bigmodel.cn/api/paas/v4" data-model="glm-4-flash">智谱 GLM</button>
      <button class="preset" data-url="https://api.siliconflow.cn/v1" data-model="Qwen/Qwen2.5-7B-Instruct">硅基流动</button>
      <button class="preset" data-url="http://localhost:11434/v1" data-model="llama3">Ollama 本地</button>
    </div>
  </div>
  <div class="field">
    <label>模型</label>
    <input id="model" type="text" value="" placeholder="deepseek-chat">
  </div>
  <div class="field">
    <label>API Key</label>
    <input id="apiKey" type="password" value="" placeholder="sk-...">
    <div class="hint">保存在 VS Code 的加密存储中，不会写入配置文件</div>
  </div>
</div>

<div class="section">
  <h2>Python 解释器</h2>
  <div class="field">
    <label>Python 路径</label>
    <input id="pythonPath" type="text" value="" placeholder="python 或 C:\\Python\\python.exe">
    <div class="hint">留空或填 python 时自动探测。如果运行报「Python was not found」请填绝对路径</div>
    <div class="test-row">
      <button class="test-btn" id="testPython">测试</button>
      <span class="test-result" id="testResult"></span>
    </div>
  </div>
  <div class="field">
    <label>hx.py 路径（可选）</label>
    <input id="interpreterPath" type="text" value="" placeholder="留空自动查找扩展内置的 hx.py">
    <div class="hint">留空时按顺序查找：工作区 hx.py → 扩展内置 python/hx.py</div>
  </div>
</div>

<div class="actions">
  <button class="btn secondary" id="cancel">取消</button>
  <button class="btn primary" id="save">保存</button>
</div>

<script nonce="${nonce}">
const vscode = acquireVsCodeApi();
const current = ${data};

const $ = (id) => document.getElementById(id);
$('baseUrl').value = current.baseUrl || '';
$('model').value = current.model || '';
$('apiKey').value = current.apiKey || '';
$('pythonPath').value = current.pythonPath || '';
$('interpreterPath').value = current.interpreterPath || '';

document.querySelectorAll('.preset').forEach((btn) => {
  btn.onclick = () => {
    $('baseUrl').value = btn.dataset.url;
    $('model').value = btn.dataset.model;
    $('apiKey').focus();
  };
});

$('testPython').onclick = () => {
  const r = $('testResult');
  r.textContent = '测试中…';
  r.className = 'test-result';
  vscode.postMessage({ type: 'test', path: $('pythonPath').value });
};

$('save').onclick = () => {
  vscode.postMessage({
    type: 'save',
    data: {
      baseUrl: $('baseUrl').value.trim(),
      model: $('model').value.trim(),
      apiKey: $('apiKey').value.trim(),
      pythonPath: $('pythonPath').value.trim(),
      interpreterPath: $('interpreterPath').value.trim(),
    },
  });
};

$('cancel').onclick = () => vscode.postMessage({ type: 'cancel' });

window.addEventListener('message', (e) => {
  const { type, ok, message } = e.data;
  if (type === 'testResult') {
    const r = $('testResult');
    r.textContent = message;
    r.className = 'test-result ' + (ok ? 'ok' : 'err');
  }
});
</script>
</body>
</html>`;
}
