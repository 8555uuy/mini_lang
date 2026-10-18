"""HX 语法检查器 - 供 VS Code 扩展调用
从 stdin 读代码，输出 JSON 诊断结果
"""
import sys, os, json, io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check(src):
    errors = []
    try:
        from hx import tokenize, Parser, MiniError
        try:
            toks = tokenize(src)
        except SyntaxError as e:
            msg = str(e)
            line, col = _parse_pos(msg)
            errors.append({"line": line, "col": col, "endLine": line, "endCol": col + 1, "message": msg, "severity": "error"})
            return errors
        except Exception as e:
            errors.append({"line": 1, "col": 1, "endLine": 1, "endCol": 2, "message": str(e), "severity": "error"})
            return errors

        try:
            Parser(toks).program()
        except SyntaxError as e:
            msg = str(e)
            line, col = _parse_pos(msg)
            errors.append({"line": line, "col": col, "endLine": line, "endCol": col + 1, "message": msg, "severity": "error"})
        except Exception as e:
            msg = str(e)
            line, col = _parse_pos(msg)
            errors.append({"line": line, "col": col, "endLine": line, "endCol": col + 1, "message": msg, "severity": "error"})
    except ImportError as e:
        errors.append({"line": 1, "col": 1, "endLine": 1, "endCol": 2, "message": "无法加载 hx.py：" + str(e), "severity": "error"})
    return errors


def _parse_pos(msg):
    """从错误信息里提取行列号：第 N 行第 M 列"""
    import re
    line = 1
    col = 1
    m = re.search(r"第 (\d+) 行", msg)
    if m:
        line = int(m.group(1))
    m = re.search(r"第 (\d+) 列", msg)
    if m:
        col = int(m.group(1))
    return line, col


def main():
    # 强制 UTF-8 输出，避免 Windows 默认 GBK 导致中文乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        src = sys.stdin.buffer.read().decode("utf-8", "replace")
    except Exception:
        src = ""
    result = check(src)
    sys.stdout.write(json.dumps({"errors": result}, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
