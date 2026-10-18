# 生成 .hxg 文件图标（多尺寸 .ico）
from PIL import Image, ImageDraw, ImageFont
import os

def rounded(draw, box, r, fill):
    x0,y0,x1,y1 = box
    draw.rounded_rectangle(box, radius=r, fill=fill)

def make(size):
    S = size*4
    img = Image.new("RGBA", (S,S), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # 背景圆角方块：深蓝渐变感（两层）
    rounded(d,(0,0,S-1,S-1), int(S*0.20), (14,99,156,255))
    rounded(d,(int(S*0.045),int(S*0.045),int(S*0.955),int(S*0.955)), int(S*0.17), (23,32,42,255))
    # 左侧强调条
    d.rounded_rectangle((int(S*0.045),int(S*0.045),int(S*0.16),int(S*0.955)), radius=int(S*0.05), fill=(86,156,214,255))
    # 文本 HX
    txt="HX"
    fs=int(S*0.40)
    font=None
    for name in ("consolab.ttf","consola.ttf","arialbd.ttf","arial.ttf"):
        for base in (os.environ.get("WINDIR","C:/Windows")+"/Fonts/", ""):
            try:
                font=ImageFont.truetype(base+name, fs); break
            except Exception: font=None
        if font: break
    if font is None:
        font=ImageFont.load_default()
    bbox=d.textbbox((0,0),txt,font=font)
    tw=bbox[2]-bbox[0]; th=bbox[3]-bbox[1]
    tx=int((S-tw)/2 - bbox[0]) + int(S*0.05)
    ty=int((S-th)/2 - bbox[1])
    # 阴影
    d.text((tx+2,ty+2),txt,font=font,fill=(0,0,0,110))
    d.text((tx,ty),txt,font=font,fill=(220,220,170,255))
    return img.resize((size,size), Image.LANCZOS)

sizes=[16,24,32,48,64,128,256]
imgs=[make(s) for s in sizes]
imgs[-1].save("hx.ico", format="ICO", sizes=[(s,s) for s in sizes])
print("hx.ico written")
