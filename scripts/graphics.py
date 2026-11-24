"""Royalty-free typographic artwork generated locally. No external image assets."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math, random

FONTS=[Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
COLORS={"gold":(220,174,97),"red":(221,98,92),"teal":(94,190,181)}


def font(px, bold=True):
    candidates=[FONTS[0],FONTS[1]] if bold else [FONTS[1],FONTS[0]]
    for path in candidates:
        if path.exists(): return ImageFont.truetype(str(path),px)
    return ImageFont.load_default()


def wrapped_lines(draw, text, f, max_width):
    chunks=[];line=''
    for word in text.split():
        test=(line+' '+word).strip()
        if draw.textbbox((0,0),test,font=f)[2]<=max_width:
            line=test
        else:
            if line: chunks.append(line)
            line=word
    if line: chunks.append(line)
    return chunks


def draw_text(d,text,xy,max_width,fs,fill,bold=True,leading=1.25,max_lines=10):
    f=font(fs,bold)
    lines=wrapped_lines(d,text,f,max_width)
    if len(lines)>max_lines:
        # Reduce the font size rather than silently crop facts.
        while len(lines)>max_lines and fs>22:
            fs-=2;f=font(fs,bold);lines=wrapped_lines(d,text,f,max_width)
    x,y=xy
    for line in lines:
        d.text((x,y),line,font=f,fill=fill,stroke_width=0)
        y+=round(fs*leading)
    return y


def render_card(path,topic,heading,main,footer,portrait=True,kind='intro'):
    w,h=(720,1280) if portrait else (1080,1350)
    accent=COLORS.get(topic['color'],COLORS['gold'])
    im=Image.new('RGB',(w,h))
    d=ImageDraw.Draw(im)
    for y in range(h):
        t=y/max(h-1,1)
        wave=0.04*math.sin(t*math.pi*2)
        row=(round(8+11*t+wave*10),round(21+8*t),round(35+13*t))
        d.line((0,y,w,y), fill=row)
    rng=random.Random(topic['id']+kind)
    for i in range(110):
        x=rng.randrange(w);y=rng.randrange(h);rr=rng.choice([1,1,2])
        d.ellipse((x,y,x+rr,y+rr),fill=(45,56,69))
    pad=round(w*.09); max_width=w-2*pad
    d.rectangle((pad,round(h*.07),w-pad,round(h*.076)),fill=accent)
    d.text((pad,round(h*.096)),"TARİHİN BİLİNMEYEN GERÇEKLERİ  /  BELGELİ HİKÂYELER",font=font(20 if portrait else 26),fill=accent)
    d.text((pad,round(h*.185)),topic['era'],font=font(25 if portrait else 31,bold=False),fill=(206,213,223))
    heading_fs=44 if portrait else 51
    main_fs=58 if portrait else 70
    y=draw_text(d,heading.upper(),(pad,round(h*.28)),max_width,heading_fs,accent,max_lines=3)
    y+=round(h*.025)
    draw_text(d,main,(pad,y),max_width,main_fs,(249,245,232),max_lines=6,leading=1.22)
    d.line((pad,h-round(h*.165),w-pad,h-round(h*.165)),fill=(86,101,111),width=2)
    draw_text(d,footer,(pad,h-round(h*.135)),max_width,22 if portrait else 26,(199,207,217),bold=False,max_lines=2)
    d.text((pad,h-round(h*.05)),"TARİHÎ CANLANDIRMA / KAYNAKLI ANLATIM",font=font(16 if portrait else 20,bold=False),fill=(135,147,159))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);im.save(path,optimize=True)
    return path
