import * as vscode from 'vscode';

/** 与 hx.py 的 UI_COMPONENTS 保持一致 */
const COMPONENTS = [
    { kind: 'title', label: '标题', group: '基础', w: 240, h: 36, text: '标题文字', fields: ['id', 'x', 'y', 'w', 'h', 'text'] },
    { kind: 'label', label: '标签', group: '基础', w: 120, h: 26, text: '标签', fields: ['id', 'x', 'y', 'w', 'h', 'text'] },
    { kind: 'button', label: '按钮', group: '基础', w: 100, h: 32, text: '按钮', fields: ['id', 'x', 'y', 'w', 'h', 'text'] },
    { kind: 'input', label: '输入框', group: '输入', w: 180, h: 28, fields: ['id', 'x', 'y', 'w', 'h'] },
    { kind: 'text', label: '多行文本', group: '输入', w: 220, h: 100, fields: ['id', 'x', 'y', 'w', 'h'] },
    { kind: 'check', label: '勾选框', group: '输入', text: '选项', fields: ['id', 'x', 'y', 'text'] },
    { kind: 'radio', label: '单选组', group: '输入', w: 160, h: 78, items: ['选项 A', '选项 B', '选项 C'], fields: ['id', 'x', 'y', 'w', 'h', 'items'] },
    { kind: 'combo', label: '下拉框', group: '输入', w: 160, h: 28, items: ['选项 A', '选项 B'], fields: ['id', 'x', 'y', 'w', 'h', 'items'] },
    { kind: 'list', label: '列表框', group: '输入', w: 160, h: 100, items: ['项目 1', '项目 2', '项目 3'], fields: ['id', 'x', 'y', 'w', 'h', 'items'] },
    { kind: 'range', label: '滑块', group: '输入', w: 180, max: 100, fields: ['id', 'x', 'y', 'w', 'max'] },
    { kind: 'progress', label: '进度条', group: '显示', w: 200, h: 18, fields: ['id', 'x', 'y', 'w', 'h'] },
    { kind: 'image', label: '图片', group: '显示', w: 160, h: 120, fields: ['id', 'x', 'y', 'w', 'h'] },
    { kind: 'table', label: '表格', group: '显示', w: 280, h: 120, items: ['列 1', '列 2', '列 3'], fields: ['id', 'x', 'y', 'w', 'h', 'items'] },
    { kind: 'panel', label: '面板', group: '布局', w: 200, h: 120, fields: ['id', 'x', 'y', 'w', 'h'] },
    { kind: 'separator', label: '分割线', group: '布局', w: 240, fields: ['id', 'x', 'y', 'w'] },
    { kind: 'tabs', label: '标签页', group: '布局', w: 280, h: 160, items: ['标签 1', '标签 2'], fields: ['id', 'x', 'y', 'w', 'h', 'items'] },
];

const FUNC_MAP: Record<string, string> = {
    title: 'uiheading',
    label: 'uilabel',
    button: 'uibtn',
    input: 'uiinput',
    text: 'uitext',
    check: 'uicheck',
    radio: 'uiradio',
    combo: 'uicombo',
    list: 'uilist',
    range: 'uirange',
    progress: 'uiprogress',
    image: 'uiimage',
    table: 'uitable',
    panel: 'uipanel',
    separator: 'uiseparator',
    tabs: 'uitabs',
};

interface CompItem {
    id: string;
    kind: string;
    props: Record<string, any>;
}

function quote(s: string): string {
    return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
}

function itemsLiteral(items: string[]): string {
    return '[' + items.map(quote).join(', ') + ']';
}

export function generateCode(items: CompItem[]): string {
    const lines: string[] = ['# ===== 由 UI 画板生成 ====='];
    if (items.length === 0) {
        lines.push('# 还没有添加组件');
        lines.push('');
        lines.push('uirun();');
        return lines.join('\n');
    }
    let maxX = 0, maxY = 0;
    for (const it of items) {
        const p = it.props;
        maxX = Math.max(maxX, (p.x || 0) + (p.w || 100));
        maxY = Math.max(maxY, (p.y || 0) + (p.h || 30));
    }
    const winW = Math.max(420, maxX + 30);
    const winH = Math.max(320, maxY + 40);
    lines.push('uiwin(' + winW + ', ' + winH + ', "我的界面");');
    lines.push('');
    for (const it of items) {
        const p = it.props;
        const fn = FUNC_MAP[it.kind];
        if (!fn) continue;
        const label = COMPONENTS.find(c => c.kind === it.kind)?.label || it.kind;
        lines.push('# ' + label + ' ' + it.id);
        const id = quote(it.id);
        switch (it.kind) {
            case 'title':
            case 'label':
            case 'button':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + p.h + ', ' + quote(p.text || '') + ');');
                break;
            case 'check':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + quote(p.text || '') + ');');
                break;
            case 'radio':
            case 'combo':
            case 'list':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + p.h + ', ' + itemsLiteral(p.items || []) + ');');
                break;
            case 'table':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + p.h + ', ' + itemsLiteral(p.items || []) + ');');
                break;
            case 'tabs':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + p.h + ', ' + itemsLiteral(p.items || []) + ');');
                break;
            case 'range':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + (p.max || 100) + ');');
                break;
            case 'separator':
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ');');
                break;
            default:
                lines.push(fn + '(' + id + ', ' + p.x + ', ' + p.y + ', ' + p.w + ', ' + p.h + ');');
        }
        lines.push('');
    }
    lines.push('# 事件处理（按需修改）');
    lines.push('on_click() {');
    lines.push('    print("按钮被点击");');
    lines.push('}');
    lines.push('');
    lines.push('uirun();');
    return lines.join('\n');
}

export class DesignerPanel {
    public static currentPanel: DesignerPanel | undefined;
    private readonly panel: vscode.WebviewPanel;
    private readonly context: vscode.ExtensionContext;
    private readonly disposables: vscode.Disposable[] = [];

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.panel = vscode.window.createWebviewPanel(
            'hxDesigner',
            'HX UI 画板',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );
        this.panel.webview.html = this.getHtml();
        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
        this.panel.webview.onDidReceiveMessage(
            (msg) => this.onMessage(msg),
            null,
            this.disposables
        );
    }

    reveal() {
        this.panel.reveal(vscode.ViewColumn.Beside);
    }

    onDidDispose(cb: () => void) {
        this.panel.onDidDispose(cb, null, this.disposables);
    }

    private async onMessage(msg: any) {
        if (msg.type === 'generate') {
            const code = generateCode(msg.items || []);
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'hx') {
                await editor.edit(b => b.insert(editor.selection.active, '\n' + code + '\n'));
                vscode.window.showInformationMessage('已插入 ' + (msg.items || []).length + ' 个组件的代码');
            } else {
                const doc = await vscode.workspace.openTextDocument({
                    language: 'hx',
                    content: code,
                });
                await vscode.window.showTextDocument(doc, { preview: false });
                vscode.window.showInformationMessage('已生成新文件（当前没有打开的 HX 文件）');
            }
        } else if (msg.type === 'preview') {
            const code = generateCode(msg.items || []);
            const doc = await vscode.workspace.openTextDocument({ language: 'hx', content: code });
            await vscode.window.showTextDocument(doc, { preview: false });
        }
    }

    private getHtml(): string {
        const compJson = JSON.stringify(COMPONENTS);
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
  background: var(--vscode-editor-background);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#topbar {
  height: 42px;
  border-bottom: 1px solid var(--vscode-panel-border);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 10px;
  flex-shrink: 0;
  background: var(--vscode-sideBar-background);
}
#topbar .title { font-weight: 600; font-size: 13px; }
#topbar .hint { color: var(--vscode-descriptionForeground); font-size: 11px; }
#topbar .spacer { flex: 1; }
#topbar button {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 3px;
  padding: 5px 14px;
  font-size: 12px;
  cursor: pointer;
}
#topbar button:hover { background: var(--vscode-button-hoverBackground); }
#topbar button.secondary {
  background: transparent;
  color: var(--vscode-foreground);
  border: 1px solid var(--vscode-panel-border);
}
#body {
  flex: 1;
  display: flex;
  overflow: hidden;
}
#palette {
  width: 190px;
  flex-shrink: 0;
  background: var(--vscode-sideBar-background);
  border-right: 1px solid var(--vscode-panel-border);
  overflow-y: auto;
}
.group-title {
  padding: 8px 12px 4px;
  font-size: 10px;
  font-weight: 700;
  color: var(--vscode-descriptionForeground);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.comp-item {
  padding: 7px 14px;
  cursor: grab;
  user-select: none;
  border-left: 2px solid transparent;
}
.comp-item:hover { background: var(--vscode-list-hoverBackground); }
.comp-item:active { cursor: grabbing; }
#canvas-wrap {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: var(--vscode-editor-background);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}
#canvas {
  position: relative;
  width: 800px;
  height: 600px;
  background: #fafaf9;
  border: 1px solid var(--vscode-panel-border);
  border-radius: 4px;
  background-image:
    linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px);
  background-size: 10px 10px;
  flex-shrink: 0;
}
#canvas.drop-target { outline: 2px dashed var(--vscode-focusBorder); outline-offset: -4px; }
.node {
  position: absolute;
  cursor: move;
  user-select: none;
  border: 1px solid #b8b6b1;
  background: #ffffff;
  overflow: hidden;
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #1c1917;
}
.node.selected {
  outline: 2px solid #c2410c;
  outline-offset: -1px;
  z-index: 10;
}
.node .handle {
  position: absolute;
  width: 7px;
  height: 7px;
  background: #ffffff;
  border: 1.5px solid #c2410c;
}
.node .handle.se { right: -4px; bottom: -4px; cursor: nwse-resize; }
.node.title { font-size: 15px; font-weight: 700; border: none; background: transparent; }
.node.label { border: 1px dashed #d8d6d1; background: transparent; padding-left: 4px; }
.node.button { background: #e8e6e2; justify-content: center; border-radius: 4px; }
.node.input { background: #ffffff; padding-left: 6px; color: #b0aea9; }
.node.text { background: #ffffff; padding: 6px; align-items: flex-start; color: #b0aea9; }
.node.check { border: none; background: transparent; }
.node.check::before { content: ''; display: inline-block; width: 12px; height: 12px; border: 1px solid #888; background: #fff; margin-right: 6px; flex-shrink: 0; }
.node.radio { border: none; background: transparent; display: block; padding: 4px 6px; }
.node.radio .opt::before { content: ''; display: inline-block; width: 10px; height: 10px; border: 1px solid #888; border-radius: 50%; background: #fff; margin-right: 6px; }
.node.combo { background: #fff; padding-left: 6px; justify-content: space-between; padding-right: 6px; }
.node.combo::after { content: '▾'; color: #888; }
.node.list { background: #fff; display: block; padding: 4px; }
.node.range { border: none; background: transparent; }
.node.progress { background: #e8e6e2; border-radius: 3px; }
.node.progress .fill { position: absolute; left: 0; top: 0; bottom: 0; background: #2f7fd8; width: 60%; border-radius: 3px 0 0 3px; }
.node.image { background: #f0eeea; justify-content: center; color: #b0aea9; }
.node.image::after { content: ''; position: absolute; inset: 0; background: linear-gradient(45deg, transparent 49.5%, #d8d6d1 49.5%, #d8d6d1 50.5%, transparent 50.5%), linear-gradient(-45deg, transparent 49.5%, #d8d6d1 49.5%, #d8d6d1 50.5%, transparent 50.5%); }
.node.image span { position: relative; z-index: 1; }
.node.table { background: #fff; display: block; padding: 0; }
.node.table .head { background: #f0eeea; display: flex; border-bottom: 1px solid #d8d6d1; }
.node.table .head .cell { flex: 1; text-align: center; padding: 4px; font-weight: 600; font-size: 10px; border-right: 1px solid #e8e6e2; }
.node.panel { background: #fff; border-radius: 4px; align-items: flex-start; padding: 6px; color: #b0aea9; }
.node.separator { border: none; background: transparent; height: 1px !important; }
.node.separator::after { content: ''; display: block; width: 100%; height: 1px; background: #9c9a95; }
.node.tabs { background: #fff; display: block; padding: 0; }
.node.tabs .tabs-bar { display: flex; border-bottom: 1px solid #d8d6d1; background: #f0eeea; }
.node.tabs .tab { padding: 5px 12px; border-right: 1px solid #e8e6e2; font-size: 10px; }
.node.tabs .tab.active { background: #fff; }
#props {
  width: 240px;
  flex-shrink: 0;
  background: var(--vscode-sideBar-background);
  border-left: 1px solid var(--vscode-panel-border);
  overflow-y: auto;
  padding: 12px;
}
#props .title { font-weight: 600; font-size: 12px; margin-bottom: 4px; }
#props .id { font-family: var(--vscode-editor-font-family); font-size: 11px; color: var(--vscode-descriptionForeground); margin-bottom: 12px; }
#props label { display: block; font-size: 10px; color: var(--vscode-descriptionForeground); margin-top: 8px; margin-bottom: 3px; }
#props input {
  width: 100%;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, transparent);
  border-radius: 3px;
  padding: 4px 6px;
  font-size: 12px;
  font-family: var(--vscode-editor-font-family);
  outline: none;
}
#props input:focus { border-color: var(--vscode-focusBorder); }
#props .delete-btn {
  margin-top: 16px;
  width: 100%;
  background: #3a2020;
  color: #e07070;
  border: none;
  border-radius: 3px;
  padding: 6px;
  font-size: 12px;
  cursor: pointer;
}
#props .delete-btn:hover { background: #4a2525; }
#statusbar {
  height: 22px;
  border-top: 1px solid var(--vscode-panel-border);
  padding: 0 14px;
  display: flex;
  align-items: center;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
  background: var(--vscode-sideBar-background);
  flex-shrink: 0;
}
</style>
</head>
<body>
<div id="topbar">
  <span class="title">UI 画板</span>
  <span class="hint">从左侧拖组件到画布</span>
  <span class="spacer"></span>
  <button class="secondary" id="btn-clear">清空</button>
  <button class="secondary" id="btn-preview">预览代码</button>
  <button id="btn-generate">生成代码</button>
</div>
<div id="body">
  <div id="palette"></div>
  <div id="canvas-wrap">
    <div id="canvas"></div>
  </div>
  <div id="props"></div>
</div>
<div id="statusbar">就绪</div>
<script nonce="${nonce}">
const vscode = acquireVsCodeApi();
const COMPONENTS = ${compJson};
const FUNC_MAP = {
  title: 'uiheading', label: 'uilabel', button: 'uibtn',
  input: 'uiinput', text: 'uitext', check: 'uicheck',
  radio: 'uiradio', combo: 'uicombo', list: 'uilist',
  range: 'uirange', progress: 'uiprogress', image: 'uiimage',
  table: 'uitable', panel: 'uipanel', separator: 'uiseparator', tabs: 'uitabs'
};
const FIELD_LABELS = {
  id: '标识', x: 'X', y: 'Y', w: '宽', h: '高',
  text: '文字', items: '选项（逗号分隔）', max: '最大值'
};

let items = [];
let selectedId = null;
let nextNum = 1;
let dragState = null;
let resizeState = null;

const canvas = document.getElementById('canvas');
const paletteEl = document.getElementById('palette');
const propsEl = document.getElementById('props');
const statusEl = document.getElementById('statusbar');

function setStatus(text) {
  statusEl.textContent = text;
}

function nextId() {
  const used = new Set(items.map(i => i.id));
  let n = nextNum;
  while (used.has('w' + n)) n++;
  nextNum = n + 1;
  return 'w' + n;
}

function buildPalette() {
  let lastGroup = '';
  for (const c of COMPONENTS) {
    if (c.group !== lastGroup) {
      const t = document.createElement('div');
      t.className = 'group-title';
      t.textContent = c.group;
      paletteEl.appendChild(t);
      lastGroup = c.group;
    }
    const el = document.createElement('div');
    el.className = 'comp-item';
    el.textContent = c.label;
    el.draggable = true;
    el.ondragstart = (e) => {
      e.dataTransfer.setData('text/plain', 'hx-comp:' + c.kind);
      e.dataTransfer.effectAllowed = 'copy';
    };
    paletteEl.appendChild(el);
  }
}

function render() {
  canvas.innerHTML = '';
  for (const it of items) {
    const p = it.props;
    const el = document.createElement('div');
    el.className = 'node ' + it.kind;
    el.dataset.id = it.id;
    el.style.left = (p.x || 0) + 'px';
    el.style.top = (p.y || 0) + 'px';
    el.style.width = (p.w || 100) + 'px';
    el.style.height = (p.h || 30) + 'px';
    if (it.id === selectedId) el.classList.add('selected');

    // 内容
    if (it.kind === 'radio') {
      const opts = p.items || [];
      el.innerHTML = opts.map(o => '<div class="opt">' + escapeHtml(o) + '</div>').join('');
    } else if (it.kind === 'list') {
      const its = p.items || [];
      el.innerHTML = its.slice(0, 8).map(o => '<div>' + escapeHtml(o) + '</div>').join('');
    } else if (it.kind === 'combo') {
      el.textContent = '下拉';
    } else if (it.kind === 'progress') {
      el.innerHTML = '<div class="fill"></div>';
    } else if (it.kind === 'table') {
      const cols = p.items || [];
      el.innerHTML = '<div class="head">' + cols.map(c => '<div class="cell">' + escapeHtml(c) + '</div>').join('') + '</div>';
    } else if (it.kind === 'tabs') {
      const its = p.items || [];
      el.innerHTML = '<div class="tabs-bar">' + its.map((t, i) => '<div class="tab' + (i === 0 ? ' active' : '') + '">' + escapeHtml(t) + '</div>').join('') + '</div>';
    } else if (it.kind === 'image') {
      el.innerHTML = '<span>图片</span>';
    } else if (it.kind === 'panel') {
      el.textContent = '面板';
    } else if (it.kind === 'input') {
      el.textContent = '输入';
    } else if (it.kind === 'text') {
      el.textContent = '多行文本';
    } else if (it.kind === 'range') {
      el.innerHTML = '<input type="range" min="0" max="' + (p.max || 100) + '" style="width:100%" disabled>';
    } else if (it.kind === 'separator') {
      // 空
    } else {
      el.textContent = p.text || COMPONENTS.find(c => c.kind === it.kind).label;
    }

    // 缩放手柄
    const handle = document.createElement('div');
    handle.className = 'handle se';
    el.appendChild(handle);

    // 拖动
    el.onmousedown = (e) => {
      if (e.target.classList.contains('handle')) {
        e.stopPropagation();
        resizeState = {
          id: it.id,
          startX: e.clientX,
          startY: e.clientY,
          origW: p.w || 100,
          origH: p.h || 30,
        };
        return;
      }
      selectItem(it.id);
      dragState = {
        id: it.id,
        startX: e.clientX,
        startY: e.clientY,
        origX: p.x || 0,
        origY: p.y || 0,
      };
      e.preventDefault();
    };

    canvas.appendChild(el);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function selectItem(id) {
  selectedId = id;
  render();
  renderProps();
}

function renderProps() {
  propsEl.innerHTML = '';
  const sel = items.find(i => i.id === selectedId);
  if (!sel) {
    const hint = document.createElement('div');
    hint.style.color = 'var(--vscode-descriptionForeground)';
    hint.style.padding = '8px 0';
    hint.textContent = '选中组件后在这里编辑属性';
    propsEl.appendChild(hint);
    return;
  }
  const comp = COMPONENTS.find(c => c.kind === sel.kind);
  const title = document.createElement('div');
  title.className = 'title';
  title.textContent = comp.label;
  propsEl.appendChild(title);
  const idEl = document.createElement('div');
  idEl.className = 'id';
  idEl.textContent = sel.id;
  propsEl.appendChild(idEl);

  for (const f of comp.fields) {
    const lab = document.createElement('label');
    lab.textContent = FIELD_LABELS[f] || f;
    propsEl.appendChild(lab);
    const inp = document.createElement('input');
    const v = sel.props[f];
    inp.value = Array.isArray(v) ? v.join(', ') : (v !== undefined ? v : '');
    inp.oninput = () => {
      const raw = inp.value;
      if (['x', 'y', 'w', 'h', 'max'].includes(f)) {
        const n = parseInt(raw, 10);
        if (!isNaN(n)) sel.props[f] = n;
      } else if (f === 'items') {
        sel.props[f] = raw.split(',').map(s => s.trim()).filter(Boolean);
      } else {
        sel.props[f] = raw;
        if (f === 'id') {
          sel.id = raw;
          selectedId = raw;
        }
      }
      render();
    };
    propsEl.appendChild(inp);
  }

  const del = document.createElement('button');
  del.className = 'delete-btn';
  del.textContent = '删除组件';
  del.onclick = () => {
    items = items.filter(i => i.id !== selectedId);
    selectedId = null;
    render();
    renderProps();
    setStatus('已删除组件');
  };
  propsEl.appendChild(del);
}

// 拖放接收
canvas.ondragover = (e) => {
  if (e.dataTransfer.types.includes('text/plain')) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    canvas.classList.add('drop-target');
  }
};
canvas.ondragleave = () => {
  canvas.classList.remove('drop-target');
};
canvas.ondrop = (e) => {
  e.preventDefault();
  canvas.classList.remove('drop-target');
  const data = e.dataTransfer.getData('text/plain');
  if (!data.startsWith('hx-comp:')) return;
  const kind = data.slice(8);
  const comp = COMPONENTS.find(c => c.kind === kind);
  if (!comp) return;
  const rect = canvas.getBoundingClientRect();
  let x = e.clientX - rect.left - (comp.w || 100) / 2;
  let y = e.clientY - rect.top - (comp.h || 30) / 2;
  x = Math.max(0, Math.round(x / 10) * 10);
  y = Math.max(0, Math.round(y / 10) * 10);
  const id = nextId();
  const props = { id, x, y };
  for (const f of comp.fields) {
    if (f === 'id' || f === 'x' || f === 'y') continue;
    if (comp[f] !== undefined) props[f] = JSON.parse(JSON.stringify(comp[f]));
  }
  const item = { id, kind, props };
  items.push(item);
  selectItem(id);
  setStatus('已添加 ' + comp.label);
};

// 画布点击空白取消选中
canvas.onmousedown = (e) => {
  if (e.target === canvas) {
    selectedId = null;
    render();
    renderProps();
  }
};

// 拖动 / 缩放
window.addEventListener('mousemove', (e) => {
  if (dragState) {
    const it = items.find(i => i.id === dragState.id);
    if (!it) return;
    let nx = dragState.origX + (e.clientX - dragState.startX);
    let ny = dragState.origY + (e.clientY - dragState.startY);
    // 吸附到 10px 网格
    nx = Math.round(nx / 10) * 10;
    ny = Math.round(ny / 10) * 10;
    it.props.x = Math.max(0, nx);
    it.props.y = Math.max(0, ny);
    render();
  } else if (resizeState) {
    const it = items.find(i => i.id === resizeState.id);
    if (!it) return;
    let nw = resizeState.origW + (e.clientX - resizeState.startX);
    let nh = resizeState.origH + (e.clientY - resizeState.startY);
    nw = Math.max(20, Math.round(nw / 10) * 10);
    nh = Math.max(12, Math.round(nh / 10) * 10);
    it.props.w = nw;
    it.props.h = nh;
    render();
  }
});

window.addEventListener('mouseup', () => {
  if (dragState || resizeState) {
    dragState = null;
    resizeState = null;
    renderProps();
  }
});

// 键盘删除
window.addEventListener('keydown', (e) => {
  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
    const target = e.target as HTMLElement;
    if (target && target.tagName === 'INPUT') return;
    items = items.filter(i => i.id !== selectedId);
    selectedId = null;
    render();
    renderProps();
  }
});

document.getElementById('btn-generate').onclick = () => {
  vscode.postMessage({ type: 'generate', items });
};
document.getElementById('btn-preview').onclick = () => {
  vscode.postMessage({ type: 'preview', items });
};
document.getElementById('btn-clear').onclick = () => {
  if (items.length === 0) return;
  if (!confirm('清空所有组件？')) return;
  items = [];
  selectedId = null;
  render();
  renderProps();
  setStatus('画布已清空');
};

buildPalette();
render();
renderProps();
</script>
</body>
</html>`;
    }

    dispose() {
        DesignerPanel.currentPanel = undefined;
        this.panel.dispose();
        while (this.disposables.length) {
            const d = this.disposables.pop();
            if (d) {
                d.dispose();
            }
        }
    }
}
