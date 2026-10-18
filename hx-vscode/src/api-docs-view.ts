import * as vscode from 'vscode';
import { API_DOCS, ApiEntry } from '../api-docs';

/**
 * 侧边栏 API 速查面板
 * Activity Bar 图标 → 展示所有 HX 内置函数，可搜索，点击插入
 */
export class ApiDocsProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'hx.apiDocs';
    private view?: vscode.WebviewView;

    constructor(private readonly extensionUri: vscode.Uri) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ): void | Thenable<void> {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
        };
        webviewView.webview.html = this.getHtml();
        webviewView.webview.onDidReceiveMessage((msg) => {
            if (msg.type === 'insert') {
                this.insertToEditor(msg.code);
            } else if (msg.type === 'openCheatsheet') {
                vscode.commands.executeCommand('hx.cheatsheet');
            }
        });
    }

    private async insertToEditor(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'hx') {
            vscode.window.showWarningMessage('请先打开一个 .hxg 文件');
            return;
        }
        await editor.edit((b) => b.insert(editor.selection.active, code));
        editor.revealRange(
            new vscode.Range(editor.selection.active, editor.selection.active),
            vscode.TextEditorRevealType.InCenter
        );
    }

    private getHtml(): string {
        const data = JSON.stringify(API_DOCS);
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
  font-size: 12px;
  color: var(--vscode-foreground);
  background: var(--vscode-sideBar-background);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#search-wrap {
  padding: 8px;
  border-bottom: 1px solid var(--vscode-panel-border);
  flex-shrink: 0;
}
#search {
  width: 100%;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, transparent);
  border-radius: 3px;
  padding: 5px 8px;
  font-size: 12px;
  outline: none;
}
#search:focus { border-color: var(--vscode-focusBorder); }
#stats {
  padding: 4px 8px;
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
  border-bottom: 1px solid var(--vscode-panel-border);
  flex-shrink: 0;
}
#list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.cat {
  margin-bottom: 4px;
}
.cat-head {
  display: flex;
  align-items: center;
  padding: 5px 10px;
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.cat-head:hover { background: var(--vscode-list-hoverBackground); }
.cat-head .arrow {
  display: inline-block;
  width: 12px;
  transition: transform .12s;
  font-size: 9px;
}
.cat.collapsed .arrow { transform: rotate(-90deg); }
.cat.collapsed .cat-body { display: none; }
.cat-icon {
  display: inline-block;
  min-width: 24px;
  text-align: center;
  font-family: var(--vscode-editor-font-family);
  font-size: 9px;
  background: var(--vscode-badge-background);
  color: var(--vscode-badge-foreground);
  border-radius: 3px;
  padding: 1px 4px;
  margin-right: 6px;
}
.cat-count {
  margin-left: auto;
  font-weight: 400;
  opacity: 0.6;
}
.entry {
  padding: 6px 10px 6px 28px;
  cursor: pointer;
  border-left: 2px solid transparent;
}
.entry:hover {
  background: var(--vscode-list-hoverBackground);
  border-left-color: var(--vscode-focusBorder);
}
.entry .sig {
  font-family: var(--vscode-editor-font-family);
  font-size: 12px;
  color: var(--vscode-symbolIcon-functionForeground, #dcdcaa);
  word-break: break-all;
}
.entry .desc {
  color: var(--vscode-descriptionForeground);
  font-size: 11px;
  margin-top: 2px;
  line-height: 1.4;
}
.entry .example {
  display: none;
  margin-top: 6px;
  background: var(--vscode-textCodeBlock-background);
  border-radius: 3px;
  padding: 6px 8px;
  font-family: var(--vscode-editor-font-family);
  font-size: 11px;
  white-space: pre;
  overflow-x: auto;
  color: var(--vscode-editor-foreground);
  position: relative;
}
.entry.expanded .example { display: block; }
.entry .example .ins {
  position: absolute;
  top: 3px;
  right: 4px;
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 3px;
  padding: 2px 7px;
  font-size: 10px;
  cursor: pointer;
  opacity: 0;
  transition: opacity .15s;
}
.entry .example:hover .ins { opacity: 1; }
.empty {
  padding: 20px;
  text-align: center;
  color: var(--vscode-descriptionForeground);
  font-size: 11px;
}
#footer {
  border-top: 1px solid var(--vscode-panel-border);
  padding: 6px 8px;
  flex-shrink: 0;
}
#footer button {
  width: 100%;
  background: transparent;
  color: var(--vscode-textLink-foreground);
  border: none;
  font-size: 11px;
  cursor: pointer;
  padding: 4px;
  text-align: left;
}
#footer button:hover { text-decoration: underline; }
</style>
</head>
<body>
<div id="search-wrap">
  <input id="search" type="text" placeholder="搜索函数名或说明…" autofocus>
</div>
<div id="stats">加载中…</div>
<div id="list"></div>
<div id="footer">
  <button id="btn-cheat">打开完整语法速查 →</button>
</div>
<script nonce="${nonce}">
const vscode = acquireVsCodeApi();
const CATEGORIES = ${data};
const listEl = document.getElementById('list');
const searchEl = document.getElementById('search');
const statsEl = document.getElementById('stats');
const collapsed = new Set();

let totalEntries = 0;
for (const c of CATEGORIES) {
  totalEntries += c.entries.length;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function render(filter) {
  const kw = (filter || '').toLowerCase().trim();
  listEl.innerHTML = '';
  let shown = 0;
  for (const cat of CATEGORIES) {
    const matched = [];
    for (const e of cat.entries) {
      if (kw) {
        const hay = (e.name + ' ' + e.sig + ' ' + e.desc + ' ' + e.category).toLowerCase();
        if (!hay.includes(kw)) continue;
      }
      matched.push(e);
    }
    if (matched.length === 0) continue;
    shown += matched.length;

    const catEl = document.createElement('div');
    catEl.className = 'cat';
    if (collapsed.has(cat.name) && !kw) catEl.classList.add('collapsed');

    const head = document.createElement('div');
    head.className = 'cat-head';
    head.innerHTML =
      '<span class="arrow">▼</span>' +
      '<span class="cat-icon">' + esc(cat.icon) + '</span>' +
      '<span>' + esc(cat.name) + '</span>' +
      '<span class="cat-count">' + matched.length + '</span>';
    head.onclick = () => {
      if (collapsed.has(cat.name)) {
        collapsed.delete(cat.name);
        catEl.classList.remove('collapsed');
      } else {
        collapsed.add(cat.name);
        catEl.classList.add('collapsed');
      }
    };
    catEl.appendChild(head);

    const body = document.createElement('div');
    body.className = 'cat-body';
    for (const e of matched) {
      body.appendChild(renderEntry(e, !!kw));
    }
    catEl.appendChild(body);
    listEl.appendChild(catEl);
  }

  if (shown === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = kw ? '没有匹配的函数' : '（空）';
    listEl.appendChild(empty);
  }

  statsEl.textContent = kw ? shown + ' / ' + totalEntries + ' 个匹配' : '共 ' + totalEntries + ' 个函数';
}

function renderEntry(e, autoExpand) {
  const el = document.createElement('div');
  el.className = 'entry';
  if (autoExpand && e.example) el.classList.add('expanded');

  const sig = document.createElement('div');
  sig.className = 'sig';
  sig.textContent = e.sig;
  el.appendChild(sig);

  const desc = document.createElement('div');
  desc.className = 'desc';
  desc.textContent = e.desc;
  el.appendChild(desc);

  if (e.example) {
    const ex = document.createElement('div');
    ex.className = 'example';
    ex.textContent = e.example;
    const btn = document.createElement('button');
    btn.className = 'ins';
    btn.textContent = '插入';
    btn.onclick = (ev) => {
      ev.stopPropagation();
      vscode.postMessage({ type: 'insert', code: e.example });
    };
    ex.appendChild(btn);
    el.appendChild(ex);
  }

  el.onclick = (ev) => {
    if (ev.target.classList.contains('ins')) return;
    el.classList.toggle('expanded');
  };

  return el;
}

searchEl.addEventListener('input', () => render(searchEl.value));
document.getElementById('btn-cheat').onclick = () => {
  vscode.postMessage({ type: 'openCheatsheet' });
};

render('');
</script>
</body>
</html>`;
    }
}
