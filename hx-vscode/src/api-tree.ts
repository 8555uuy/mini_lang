import * as vscode from 'vscode';
import { API_DOCS, ApiEntry, ApiCategory } from './api-docs';

/**
 * API 速查的 TreeView 实现
 * 完全不用 Webview，兼容所有 VS Code 衍生版
 */

class ApiItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly kind: 'category' | 'entry',
        public readonly data: ApiCategory | ApiEntry
    ) {
        super(label, collapsibleState);
        this.contextValue = kind;
        if (kind === 'category') {
            const cat = data as ApiCategory;
            this.description = String(cat.entries.length) + ' 个';
            this.iconPath = new vscode.ThemeIcon('symbol-class');
        } else {
            const e = data as ApiEntry;
            this.description = e.desc;
            this.iconPath = new vscode.ThemeIcon('symbol-function');
            this.tooltip = new vscode.MarkdownString();
            this.tooltip.appendCodeblock(e.sig, 'hx');
            this.tooltip.appendMarkdown('\n\n' + e.desc);
            if (e.example) {
                this.tooltip.appendMarkdown('\n\n**示例**\n\n');
                this.tooltip.appendCodeblock(e.example, 'hx');
            }
            // 点击时插入示例代码
            this.command = {
                command: 'hx.insertApiExample',
                title: '插入示例',
                arguments: [e],
            };
        }
    }
}

export class ApiTreeProvider implements vscode.TreeDataProvider<ApiItem> {
    private _onDidChange = new vscode.EventEmitter<ApiItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChange.event;
    private filter = '';

    getTreeItem(element: ApiItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ApiItem): ApiItem[] {
        if (!element) {
            // 顶层：分类
            const kw = this.filter.toLowerCase();
            const out: ApiItem[] = [];
            for (const cat of API_DOCS) {
                if (kw) {
                    const matched = cat.entries.filter(e =>
                        (e.name + ' ' + e.sig + ' ' + e.desc).toLowerCase().includes(kw)
                    );
                    if (matched.length === 0) {
                        continue;
                    }
                }
                out.push(new ApiItem(
                    cat.name,
                    kw ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.Collapsed,
                    'category',
                    cat
                ));
            }
            return out;
        }
        // 展开分类：返回函数
        if (element.kind === 'category') {
            const cat = element.data as ApiCategory;
            const kw = this.filter.toLowerCase();
            const entries = kw
                ? cat.entries.filter(e => (e.name + ' ' + e.sig + ' ' + e.desc).toLowerCase().includes(kw))
                : cat.entries;
            return entries.map(e => new ApiItem(
                e.sig,
                vscode.TreeItemCollapsibleState.None,
                'entry',
                e
            ));
        }
        return [];
    }

    setFilter(f: string) {
        this.filter = f;
        this._onDidChange.fire(undefined);
    }

    getFilter() {
        return this.filter;
    }
}
