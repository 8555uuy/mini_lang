# 把根目录 hx.py 同步到扩展内置副本
import shutil, os
src = "hx.py"
dst = "hx-vscode/python/hx.py"
shutil.copy2(src, dst)
print("synced: %s -> %s (%d bytes)" % (src, dst, os.path.getsize(dst)))
