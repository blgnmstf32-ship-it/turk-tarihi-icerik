"""Five original, animated-camera-ready historic reconstructions; no stock/copyright files.

These are STYLIZED drawings, not photographs or historically verified uniforms/maps.
"""
from __future__ import annotations
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=720,1280
FONTS=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']

def font(n):
    for f in FONTS:
        try: return ImageFont.truetype(f,n)
        except OSError:pass
    return ImageFont.load_default()

def textwrap(text, maxw, draw, ft):
    out=[];line=''
    for word in text.split():
        trial=(line+' '+word).strip()
        if draw.textbbox((0,0),trial,font=ft)[2] > maxw and line:
            out.append(line);line=word
        else:line=trial
    if line:out.append(line)
    return out

def horse(d,x,y,s,c):
    # silhouette: horse body, neck, head, legs, tail; intentionally stylized.
    d.ellipse((x-72*s,y-23*s,x+48*s,y+25*s),fill=c)
    d.polygon([(x+24*s,y-18*s),(x+62*s,y-78*s),(x+83*s,y-65*s),(x+55*s,y+9*s)],fill=c)
    d.ellipse((x+62*s,y-85*s,x+105*s,y-59*s),fill=c)
    d.polygon([(x+68*s,y-83*s),(x+74*s,y-102*s),(x+82*s,y-82*s)],fill=c)
    for dx,dd in [(-45,-19),(-22,12),(20,-5),(39,15)]:
        d.line((x+dx*s,y+12*s,x+(dx+dd)*s,y+90*s),fill=c,width=max(2,int(9*s)))
    d.polygon([(x-65*s,y-10*s),(x-119*s,y-53*s),(x-102*s,y-7*s)],fill=c)

def rider(d,x,y,s,c,flag=False):
    horse(d,x,y,s,c)
    d.ellipse((x-8*s,y-100*s,x+23*s,y-66*s),fill=c)
    d.polygon([(x-22*s,y-67*s),(x+39*s,y-68*s),(x+22*s,y-18*s),(x-13*s,y-18*s)],fill=c)
    d.line((x+14*s,y-65*s,x+58*s,y-9*s),fill=c,width=max(2,int(7*s)))
    if flag:
        d.line((x-16*s,y-85*s,x-18*s,y-250*s),fill='#262426',width=max(2,int(6*s)))
        d.polygon([(x-18*s,y-240*s),(x-120*s,y-205*s),(x-18*s,y-175*s)],fill='#ad6339')

def scene(topic,i,dest):
    random.seed(17+i)
    palettes=[('#101b32','#bd6f45','#f1b56d'),('#0b202f','#647f87','#d3b782'),('#222033','#b58456','#f7dbb3'),('#0c2735','#3d667c','#bbd2bd'),('#10202d','#b86c3f','#d29a6a')]
    sky,land,glow=palettes[i]
    img=Image.new('RGB',(W,H));p=img.load()
    # graded sky, slight atmospheric haze
    sr,sg,sb=tuple(int(sky[j:j+2],16) for j in (1,3,5));lr,lg,lb=tuple(int(glow[j:j+2],16) for j in (1,3,5))
    for y in range(H):
        t=min(.85,max(0,(y/H-.08)*1.1))
        c=(int(sr*(1-t)+lr*t*.57),int(sg*(1-t)+lg*t*.52),int(sb*(1-t)+lb*t*.42))
        ImageDraw.Draw(img).line((0,y,W,y),fill=c)
    d=ImageDraw.Draw(img)
    if i!=3:
        d.ellipse((453,160,730,440),fill=glow)
        for j in range(30):
            y=540+j*15;x1=random.randint(-70,50);x2=random.randint(460,820)
            d.ellipse((x1,y,x2,y+random.randint(5,18)),fill=land)
        d.polygon([(0,695),(90,598),(240,690),(350,570),(500,675),(605,565),(720,672),(720,1280),(0,1280)],fill='#17232b')
        d.polygon([(0,765),(110,677),(220,780),(390,690),(560,740),(680,690),(720,755),(720,1280),(0,1280)],fill=land)
    if i==0:
        for k in range(5):rider(d,85+k*145,853+30*(k%2),.70+(.17 if k==3 else 0),'#111b27',flag=(k==3))
    elif i==1:
        rider(d,405,850,1.55,'#111a25',flag=True)
        d.ellipse((-180,940,910,1280),fill='#152532')
    elif i==2:
        for k in range(8):
            x=(k%4)*200+12;y=765+(k//4)*135
            d.ellipse((x+40,y-100,x+95,y-40),fill='#18202b')
            d.polygon([(x+14,y-34),(x+125,y-35),(x+108,y+130),(x+20,y+130)],fill='#1b232d')
            d.line((x+50,y-50,x+45,y-205),fill='#28252b',width=7)
            d.polygon([(x+45,y-197),(x+132,y-175),(x+45,y-146)],fill='#86513e')
    elif i==3:
        # Explicitly NOT a real map; no unsupported battlefield routes or geographic facts.
        d.rounded_rectangle((85,340,640,975),radius=30,fill='#1b3540',outline='#bfa16e',width=6)
        for j in range(7):
            yy=400+j*80
            d.line((130,yy+random.randint(-10,10),590,yy+random.randint(-10,10)),fill='#50777a',width=3)
        d.ellipse((222,560,282,620),fill='#d49d59')
        d.ellipse((470,750,530,810),fill='#a95c49')
        d.line((270,610,300,680,385,700,460,755),fill='#e3be82',width=11,joint='curve')
        d.text((160,855),'TEMSiLi HAREKET PLANI',font=font(24),fill='#dcc5a3')
    elif i==4:
        for k in range(4):rider(d,40+k*190,885+30*(k%2),.95,'#18212c',flag=(k==2))
        d.arc((80,380,720,980),180,320,fill='#e3c593',width=8)
    # overlay content, never disguise stylization as historic photography
    overlay=Image.new('RGBA',(W,H),(0,0,0,0));od=ImageDraw.Draw(overlay)
    od.rounded_rectangle((32,60,688,148),radius=20,fill=(4,12,21,192))
    od.text((56,85),'TÜRK TARİHİ  /  TEMSİLİ CANLANDIRMA',font=font(25),fill=(241,224,195,255))
    od.rounded_rectangle((32,1010,688,1228),radius=22,fill=(4,12,21,215))
    titles=['BİR TARİHÎ DÖNÜM NOKTASI','ÖNE ÇIKAN KİŞİLER','KARŞI KARŞIYA GELEN GÜÇLER','OLAYIN BAĞLAMI','TARİHE BIRAKTIĞI İZ']
    od.text((56,1035),titles[i],font=font(25),fill=(236,183,116,255))
    facts=topic['facts'];lines=textwrap([topic['hook'],facts[0],facts[1],topic['context'] or facts[2],facts[2]][i],595,od,font(32))[:3]
    yy=1080
    for line in lines:od.text((56,yy),line,font=font(32),fill=(247,243,231,255));yy+=42
    img=Image.alpha_composite(img.convert('RGBA'),overlay).convert('RGB')
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);img.save(dest,quality=93)
    return dest

def generate(topic,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    files=[str(scene(topic,i,out/f'{i+1:02d}_scene.jpg')) for i in range(5)]
    (out/'IMAGE_PROVENANCE.md').write_text('Five original stylized images drawn in code. Illustrative reconstructions, NOT photographs, accurate uniforms, or verified geographic maps. No third-party assets.\n',encoding='utf-8')
    return files
