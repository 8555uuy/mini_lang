import * as vscode from 'vscode';

/**
 * 文档符号提供者
 * 识别 fn_name(...) { 形式的函数定义，支持 Ctrl+Shift+O 跳转
 */
export class HxDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    provideDocumentSymbols(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): vscode.SymbolInformation[] | vscode.DocumentSymbol[] {
        const symbols: vscode.SymbolInformation[] = [];
        const funcRe = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*\{/;
        const lineCount = document.lineCount;
        for (let i = 0; i < lineCount; i++) {
            const line = document.lineAt(i).text;
            const m = funcRe.exec(line);
            if (!m) {
                continue;
            }
            const name = m[1];
            const params = m[2];
            // 排除关键字误判
            if (['if', 'else', 'while', 'for', 'try', 'catch', 'return'].includes(name)) {
                continue;
            }
            const startCol = line.indexOf(name);
            const range = new vscode.Range(
                new vscode.Position(i, startCol),
                new vscode.Position(i, startCol + name.length)
            );
            const detail = params.trim() ? '(' + params.trim() + ')' : '()';
            symbols.push(
                new vscode.SymbolInformation(
                    name,
                    vscode.SymbolKind.Function,
                    detail,
                    new vscode.Location(document.uri, range)
                )
            );
        }
        return symbols;
    }
}
