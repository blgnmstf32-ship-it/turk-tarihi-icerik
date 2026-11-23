"""Eight varied, original illustrated scenes for a Malazgirt history Reel.

These are graphic, fictional reconstructions, not documentary images, maps,
uniform references, or evidence for particular battlefield tactics.
"""
from __future__ import annotations
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=900,1600
FONTS=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']
INK='#101821'; CREAM='#f7edda'; GOLD='#edb865'; PALE='#d9d4c4'; RED='#a85443'; TEAL='#426d70'

def font(n):
    for f in FONTS:
        try:return ImageFont.truetype(f,n)
        except OSError:pass
    return ImageFont.load_default()

def centered(d,xy,text,ft,fill,anchor='mm'):
    d.text(xy,text,font=ft,fill=fill,anchor=anchor,stroke_width=0)

def horse(d,x,y,s,c):
    # Angular, deliberately illustrative horse and rider silhouettes.
    d.ellipse((x-90*s,y-25*s,x+52*s,y+42*s),fill=c)
    d.polygon([(x+30*s,y-12*s),(x+67*s,y-111*s),(x+103*s,y-89*s),(x+64*s,y+25*s)],fill=c)
    d.polygon([(x+82*s,y-95*s),(x+116*s,y-115*s),(x+128*s,y-78*s),(x+99*s,y-62*s)],fill=c)
    d.polygon([(x+89*s,y-95*s),(x+90*s,y-127*s),(x+104*s,y-94*s)],fill=c)
    d.ellipse((x-14*s,y-157*s,x+27*s,y-112*s),fill=c)
    d.polygon([(x-34*s,y-118*s),(x+38*s,y-120*s),(x+55*s,y-36*s),(x-44*s,y-32*s)],fill=c)
    d.line((x-52*s,y+20*s,x-74*s,y+118*s),fill=c,width=max(2,int(13*s)))
    d.line((x-13*s,y+24*s,x+4*s,y+115*s),fill=c,width=max(2,int(12*s)))
    d.line((x+24*s,y+19*s,x+61*s,y+117*s),fill=c,width=max(2,int(12*s)))
    d.line((x+47*s,y+16*s,x+30*s,y+111*s),fill=c,width=max(2,int(12*s)))
    d.line((x-84*s,y-4*s,x-132*s,y-42*s),fill=c,width=max(2,int(7*s)))
    d.line((x-6*s,y-118*s,x-4*s,y-288*s),fill=c,width=max(2,int(7*s)))
    d.polygon([(x-4*s,y-280*s),(x+94*s,y-242*s),(x-4*s,y-204*s)],fill=GOLD)

def background(seed,top='#0b1724',bottom='#684d3f'):
    random.seed(seed);im=Image.new('RGB',(W,H));p=im.load()
    a=tuple(int(top[i:i+2],16) for i in (1,3,5));b=tuple(int(bottom[i:i+2],16) for i in (1,3,5))
    for y in range(H):
        t=(y/H)**1.25
        col=tuple(int(a[k]*(1-t)+b[k]*t) for k in range(3))
        ImageDraw.Draw(im).line((0,y,W,y),fill=col)
    return im

def mountains(d,base=1040,color='#25313a',seed=1):
    random.seed(seed);pts=[(0,base)]
    x=0
    while x<W:
        x+=random.randint(100,230);pts.append((min(x,W),base-random.randint(120,320)))
    pts.extend([(W,H),(0,H)])
    d.polygon(pts,fill=color)

def atmosphere(im,seed=0):
    d=ImageDraw.Draw(im,'RGBA');random.seed(seed)
    for _ in range(160):
        x=random.randrange(W);y=random.randrange(240,1350);r=random.choice([1,2,3,5])
        d.ellipse((x-r,y-r,x+r,y+r),fill=(255,211,145,random.randrange(15,62)))
    # Grain-like hatch lines add depth without pretending the art is a photo.
    for k in range(28):
        x=(k*83+seed*31)%W;y=870+(k*41)%430
        d.line((x,y,x+random.randint(50,160),y-random.randint(10,40)),fill=(255,226,184,18),width=2)

def scene(topic,i,dest):
    palette=[('#0a1623','#775141'),('#081c2c','#365866'),('#111b2a','#8a583c'),('#0b1b2a','#424c53'),
             ('#111723','#734638'),('#101a27','#59635b'),('#0a1b26','#4c6265'),('#0b1724','#9b6242'),
             ('#101723','#5a443c'),('#081722','#334b55')]
    top,low=palette[i];im=background(110+i,top,low);d=ImageDraw.Draw(im)
    if i in (0,4,7):
        d.ellipse((530,225,800,495),fill='#e8b477');
        mountains(d,970,'#1c2831',i)
        d.polygon([(0,1080),(160,890),(355,1055),(565,810),(760,1030),(900,885),(900,H),(0,H)],fill='#513e36')
        for k in range(3 if i==7 else 6):horse(d,70+k*150,1240+random.randint(-45,40),.56 if i==0 else .65,'#121a21')
        if i==0:
            centered(d,(450,735),'26 AĞUSTOS 1071',font(70),CREAM)
            centered(d,(450,825),'MALAZGİRT',font(100),GOLD)
        elif i==4:
            for k in range(5):
                x=80+k*165;d.line((x,950,x+28,660-random.randint(0,100)),fill='#d4b279',width=7)
            centered(d,(450,720),'İKİ ORDU',font(72),CREAM)
            centered(d,(450,805),'KARŞI KARŞIYA',font(57),GOLD)
        else:
            d.arc((70,555,835,1310),195,340,fill=GOLD,width=10)
            centered(d,(450,700),'TARİHİN AKIŞINDA',font(52),PALE)
            centered(d,(450,800),'BİR DÖNÜM NOKTASI',font(62),GOLD)
    elif i==1:
        # An abstract, explicitly non-geographic title card with a moving time line.
        for k in range(9):
            y=350+k*120
            d.arc((-220,y-140,1120,y+180),195,345,fill=('#34515a' if k%2 else '#243a46'),width=4)
        d.line((125,900,775,900),fill=GOLD,width=9)
        for x,label in [(165,'1071'),(450,'MALAZGİRT'),(735,'ANADOLU')]:
            d.ellipse((x-18,882,x+18,918),fill=CREAM)
            centered(d,(x,975),label,font(30 if x==450 else 35),CREAM)
        centered(d,(450,560),'BİR GÜN',font(60),PALE)
        centered(d,(450,650),'UZUN BİR TARİH',font(64),GOLD)
        centered(d,(450,850),'Temsilî zaman çizgisi',font(27),'#c2c4c0')
    elif i==2:
        # Close-up abstract leader, no portrait likeness or asserted uniform detail.
        d.ellipse((300,390,600,690),fill='#202935',outline=GOLD,width=8)
        d.polygon([(300,545),(370,385),(525,380),(604,550),(545,655),(345,658)],fill='#27313c',outline='#c49861')
        d.ellipse((365,442,535,610),fill='#8d664b')
        d.polygon([(340,472),(400,365),(520,365),(584,480),(465,435)],fill='#17212b',outline=GOLD)
        d.polygon([(385,536),(462,503),(533,544),(520,652),(380,652)],fill='#39444a')
        d.arc((75,325,825,1280),200,340,fill=GOLD,width=6)
        centered(d,(450,840),'SULTAN ALP ARSLAN',font(56),CREAM)
        centered(d,(450,910),'SELÇUKLU ORDUSU',font(34),GOLD)
    elif i==3:
        # Opposing command silhouettes; intentionally symbolic and non-photographic.
        d.polygon([(0,0),(470,0),(470,H),(0,H)],fill='#182536')
        d.polygon([(470,0),(W,0),(W,H),(470,H)],fill='#282b32')
        for x in (260,640):
            d.ellipse((x-82,510,x+82,675),fill='#38414a',outline=GOLD,width=5)
            d.polygon([(x-120,590),(x,405),(x+120,590)],fill='#1d2833',outline='#ba9666')
            d.polygon([(x-150,680),(x+150,680),(x+225,1180),(x-230,1180)],fill='#29333e',outline='#555c5d')
            d.line((x-80,740,x-145,1110),fill='#c9ae7c',width=8)
        d.line((450,300,450,1300),fill=GOLD,width=3)
        centered(d,(225,1040),'SELÇUKLU',font(39),CREAM)
        centered(d,(675,1040),'BİZANS',font(39),CREAM)
        centered(d,(450,340),'İKİ TARAF',font(58),GOLD)
    elif i==5:
        # Abstract clash conveyed with movement, shields and dust, no gore/tactical claim.
        for side,color in [(0,'#182430'),(1,'#41413d')]:
            for j in range(5):
                x=side*490+70+j*78;y=720+(j%2)*130
                d.ellipse((x,y,x+62,y+62),fill='#b1845b',outline=GOLD,width=3)
                d.polygon([(x-18,y+55),(x+78,y+55),(x+98,y+330),(x-38,y+330)],fill=color,outline='#89785e')
                d.line((x+26,y+55,x+20,y-95),fill='#d1b174',width=5)
        d.ellipse((350,530,550,730),outline=GOLD,width=6)
        centered(d,(450,480),'MALAZGİRT',font(60),CREAM)
    elif i==6:
        # Emphasize the long settlement process, avoiding a single-battle causality claim.
        centered(d,(450,400),'BİR GÜNDE DEĞİL',font(70),CREAM)
        centered(d,(450,505),'UZUN BİR SÜREÇ',font(74),GOLD)
        d.line((125,910,775,910),fill='#b6a27a',width=8)
        for k,(lab,sub) in enumerate([('MALAZGİRT','1071'),('ANADOLU','DÖNÜŞÜM'),('YERLEŞME','UZUN SÜREÇ')]):
            x=150+k*300
            d.ellipse((x-42,868,x+42,952),fill=GOLD if k==0 else '#d4d1c6')
            centered(d,(x,1025),lab,font(31),CREAM)
            centered(d,(x,1080),sub,font(25),PALE)
        centered(d,(450,1000),'Malazgirt önemli bir dönüm noktasıdır.',font(30),CREAM)
    elif i==8:
        # A closing visual beat with forward-moving dawn light and silhouettes.
        d.ellipse((300,320,720,740),fill='#e4aa68')
        mountains(d,1080,'#25313b',i)
        d.polygon([(0,1190),(210,930),(430,1130),(650,900),(900,1110),(900,H),(0,H)],fill='#594337')
        for k in range(3):horse(d,170+k*280,1290,.7,'#121a21')
        for k in range(7):
            y=780+k*53;d.line((0,y,900,y-155),fill=(218,171,108),width=3)
        centered(d,(450,735),'BİR EŞİKTEN',font(62),CREAM)
        centered(d,(450,825),'YENİ BİR DÖNEME',font(67),GOLD)
    elif i==9:
        # Clean end card, designed to land with the final narration phrase.
        for rad in (110,205,300,395):
            d.ellipse((450-rad,680-rad,450+rad,680+rad),outline=('#d4a762' if rad==395 else '#51616a'),width=4)
        d.line((135,1110,765,1110),fill=GOLD,width=8)
        for x in (150,450,750):d.ellipse((x-11,1099,x+11,1121),fill=CREAM)
        centered(d,(450,590),'MALAZGİRT',font(91),CREAM)
        centered(d,(450,710),'26 AĞUSTOS 1071',font(43),GOLD)
        centered(d,(450,875),'ANADOLU TARİHİNDE',font(37),PALE)
        centered(d,(450,940),'ÖNEMLİ BİR DÖNÜM NOKTASI',font(40),CREAM)
    atmosphere(im,seed=21+i)
    # Consistent branded frame and a specific, concise scene label.
    overlay=Image.new('RGBA',(W,H),(0,0,0,0));od=ImageDraw.Draw(overlay)
    od.rounded_rectangle((32,48,868,125),radius=23,fill=(5,12,18,190))
    od.text((60,69),'TÜRK TARİHİ     •     TEMSİLÎ CANLANDIRMA',font=font(28),fill=(244,228,202,255))
    labels=['MALAZGİRT • 1071','TARİHİN UZUN AKIŞI','SULTAN ALP ARSLAN','SELÇUKLU VE BİZANS','ORDULAR KARŞI KARŞIYA','ÇARPIŞMANIN SONUCU','UZUN BİR DÖNÜŞÜM','ANADOLU TARİHİNDE BİR EŞİK','YENİ BİR DÖNEME','MALAZGİRT • 26 AĞUSTOS 1071']
    od.rounded_rectangle((32,1455,868,1555),radius=20,fill=(5,12,18,185))
    od.text((60,1485),labels[i%8],font=font(31),fill=(238,190,122,255))
    im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    im=im.resize((720,1280),Image.Resampling.LANCZOS)
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest,quality=94)
    return dest

def generate(topic,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # Remove stale captures from prior attempts so fallback art and Commons
    # assets can never silently mix or inflate the scene count.
    for old in out.iterdir():
        if old.is_file() and old.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}:
            old.unlink()
    files=[str(scene(topic,i,out/f'{i+1:02d}_scene.jpg')) for i in range(10)]
    (out/'IMAGE_PROVENANCE.md').write_text(
        'Eight original vector-style illustrations made in code. They are symbolic reconstructions, not documentary images, factual maps, uniform references, or verified battle tactics. No third-party media is used.\n',encoding='utf-8')
    return files
