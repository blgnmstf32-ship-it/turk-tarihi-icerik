"""Original editorial design and sound for the first skincare Reel."""
from pathlib import Path
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE = (1080, 1920)
CREAM, ROSE, INK = "#fff3e9", "#edb8b3", "#291824"
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu")
SERIF = FONT_PATH / "DejaVuSerif.ttf"
SANS = FONT_PATH / "DejaVuSans.ttf"
BOLD = FONT_PATH / "DejaVuSans-Bold.ttf"


def font(size, face=SANS):
    return ImageFont.truetype(str(face), size)


def background():
    top = np.array([54, 30, 48], dtype=float)
    bottom = np.array([25, 18, 29], dtype=float)
    t = np.linspace(0, 1, SIZE[1])[:, None, None]
    y, x = np.ogrid[:SIZE[1], :SIZE[0]]
    halo = np.exp(-(((x-800)/555)**2 + ((y-775)/625)**2))[:, :, None]
    noise = np.random.default_rng(507).normal(0, .53, (SIZE[1], SIZE[0], 1))
    return Image.fromarray(np.uint8(np.clip(top + (bottom-top)*t + halo*[28, 11, 23] + noise, 0, 255))).convert("RGBA")


def shade(image, *, from_top):
    t = np.linspace(0, 1, SIZE[1])
    alpha = 210 * np.clip((.56-t)/.56 if from_top else (t-.38)/.62, 0, 1)**1.6
    overlay = Image.new("RGBA", SIZE, (32, 15, 30))
    overlay.putalpha(Image.fromarray(np.tile(alpha[:, None], (1, SIZE[0])).astype(np.uint8)))
    return Image.alpha_composite(image.convert("RGBA"), overlay)


def heading(draw, eyebrow, title, position=(86, 278)):
    x, y = position
    draw.rounded_rectangle((x, y-37, x+55, y-32), 2, fill=ROSE)
    draw.text((x, y), eyebrow, font=font(25, BOLD), fill=ROSE)
    draw.multiline_text((x, y+58), title, font=font(74, SERIF), fill=CREAM, spacing=11)


def cover(photo, output):
    with Image.open(photo) as source:
        image = shade(source, from_top=False)
    draw = ImageDraw.Draw(image)
    heading(draw, "GÜZELLİK VE KİŞİSEL BAKIM", "Nemlendirici için\ndoğru an", (86, 1108))
    draw.text((86, 1395), "KURU CİLT BAKIMI", font=font(29, BOLD), fill=CREAM)
    draw.text((86, 1460), "TEMSİLİ AI GÖRSELİ", font=font(20), fill=ROSE)
    image.convert("RGB").save(output, quality=94, optimize=True)


def center(draw, xy, text, size, *, face=SANS, fill=CREAM):
    draw.text(xy, text, font=font(size, face), fill=fill, anchor="mm")


def diagram(draw, kind):
    if kind == "timing":
        for pad in (0, 29, 63):
            draw.arc((225+pad, 637+pad, 855-pad, 1267-pad), 180, 493,
                     fill=ROSE if pad == 0 else "#9f677d", width=4 if pad == 0 else 2)
        center(draw, (540, 902), "5–10", 157, face=SERIF)
        center(draw, (540, 1032), "DAKİKA  /  ILIK SU", 29, face=BOLD, fill=ROSE)
    else:
        labels = {
            "damp": ("HAFİF NEMLİ CİLT", "Nemlendirici"),
            "wash": ("EL YIKAMA SONRASI", "Aynı adım"),
            "label": ("FRAGRANCE-FREE", "Parfüm içermez"),
            "gloves": ("BULAŞIK  /  UZUN SU TEMASI", "Koruyucu eldiven"),
            "cold": ("SOĞUK VE KURU HAVA", "Elleri koruyun"),
            "sources": ("KAYNAK", "AAD  ·  DermNet"),
        }
        kicker, description = labels[kind]
        draw.rounded_rectangle((88, 748, 992, 1168), 42, fill="#44283d", outline="#9f677d", width=2)
        draw.line((128, 856, 950, 856), fill="#9f677d", width=2)
        center(draw, (540, 805), kicker, 26, face=BOLD, fill=ROSE)
        center(draw, (540, 953), description, 57, face=SERIF)
        detail = {
            "damp": "Duş veya el yıkama sonrası",
            "wash": "Cilt hafif nemliyken",
            "label": "Koku maskeleyicileri için etikete bakın",
            "gloves": "Suyla uzun süre temas ederken",
            "cold": "Soğuk ve kuru havalarda",
            "sources": "Kaynak bağlantıları açıklamada",
        }
        center(draw, (540, 1060), detail[kind], 32)


def still(kind, source, target):
    if kind in {"hook", "towel"}:
        with Image.open(source) as picture:
            if kind == "towel":
                picture = picture.crop((367, 646, 1080, 1913))
            picture = picture.resize(SIZE, Image.Resampling.LANCZOS)
        picture = shade(picture, from_top=True)
    else:
        picture = background()
        diagram(ImageDraw.Draw(picture), kind)
    picture.convert("RGB").save(target, quality=93)


def overlay(target, eyebrow, title, *, visual_note=None):
    image = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(image)
    heading(draw, eyebrow, title)
    if visual_note:
        draw.rounded_rectangle((86, 1263, 83+font(25, BOLD).getlength(visual_note)+39, 1318),
                               22, fill=(39, 23, 34, 224), outline="#9f677d", width=2)
        draw.text((106, 1274), visual_note, fill=CREAM, font=font(25, BOLD))
    image.save(target, optimize=True)


def beauty_score(seconds, cuts, path):
    """Synthesize a stereo pad, soft glass notes and dry transition swells."""
    rate = 24000
    t = np.arange(round(rate*seconds), dtype=np.float32)/rate
    bed = np.zeros_like(t)
    chords = ((110, 130.81, 164.81), (87.31, 130.81, 174.61),
              (98, 146.83, 196), (82.41, 123.47, 164.81))
    for i, start in enumerate(np.arange(-3, seconds, 7.6)):
        active = np.clip((t-start)/3.2, 0, 1) * np.clip((start+10.8-t)/3.2, 0, 1)
        local = np.maximum(0, t-start-1.6)
        for j, note in enumerate(chords[i % len(chords)]):
            bed += active * .035 * np.sin(2*np.pi*note*t + .29*np.sin(t*1.1+j))
        bed += .024 * np.sin(2*np.pi*chords[i % 4][1]*4*t)*active*np.exp(-2.1*local)*np.clip(local*10, 0, 1)
    rng = np.random.default_rng(871)
    noise = rng.normal(0, 1, t.size).astype(np.float32)
    air = np.convolve(noise, np.hanning(65)/32, mode="same")
    for cut in cuts:
        bed += .055 * air * np.exp(-((t-cut)/.17)**2)
    bed *= np.clip(t/.7, 0, 1)*np.clip((seconds-t)/1.15, 0, 1)
    side = np.roll(bed, 19) * .20
    stereo = np.column_stack((bed, bed*.80 + side))
    with wave.open(str(path), "wb") as audio:
        audio.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes((stereo.clip(-1, 1)*32767).astype("<i2").tobytes())
