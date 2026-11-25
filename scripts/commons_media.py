"""Fetch Wikimedia Commons visuals only when an explicit free license is present."""
from __future__ import annotations

import html
from itertools import zip_longest
import re
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from io import BytesIO

API='https://commons.wikimedia.org/w/api.php'
MAX_BYTES=8_000_000
TARGET_SIZE=(1080,1920)


def _plain(value):
    value=value or ''
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(value)))).strip()


def _allowed_license(name):
    name=_plain(name).lower()
    if any(mark in name for mark in ('public domain','cc0','creative commons zero')):
        return True
    return bool(re.search(r'\bcc\s*by(?:\s*-\s*sa)?\s*(?:[234])(?:\.\d)?\b',name))


def _metadata(page):
    info=(page.get('imageinfo') or [{}])[0]
    meta=info.get('extmetadata') or {}
    if info.get('mediatype')!='BITMAP' or not str(info.get('mime','')).startswith('image/'):
        return None
    title=page.get('title','').removeprefix('File:')
    license_name=_plain((meta.get('LicenseShortName') or {}).get('value'))
    if not _allowed_license(license_name):
        return None
    description_url='https://commons.wikimedia.org/wiki/'+quote(page.get('title','').replace(' ','_'),safe=':/()')
    return {
        'title':_plain((meta.get('ObjectName') or {}).get('value')) or title,
        'artist':_plain((meta.get('Artist') or {}).get('value')) or 'Yazar belirtilmemiş',
        'credit':_plain((meta.get('Credit') or {}).get('value')),
        'license':license_name,
        'license_url':_plain((meta.get('LicenseUrl') or {}).get('value')),
        'description_url':description_url,
        'url':info.get('thumburl') or info.get('url'),
    }


def _fingerprint(image):
    pixels = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS).tobytes()
    result = 0
    for y in range(8):
        for x in range(8):
            result = (result << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return result


def _portrait(image):
    width, height = image.size
    if width / height <= 0.72:
        return ImageOps.fit(image, TARGET_SIZE, method=Image.Resampling.LANCZOS), 'portrait_crop'
    matte = ImageOps.fit(image, (270,480)).filter(ImageFilter.GaussianBlur(16))
    canvas = ImageEnhance.Brightness(matte.resize(TARGET_SIZE)).enhance(0.40)
    foreground = ImageOps.contain(image, (1000, 1460), method=Image.Resampling.LANCZOS)
    canvas.paste(foreground, ((1080 - foreground.width) // 2, (1740 - foreground.height) // 2))
    return canvas, 'full_image_on_matte'


def fetch_visuals(topic, output_dir, session=requests, limit=10):
    """Search curated topic terms, save diverse licensed images and attribution.

    Returns an empty list on network/API problems; callers must use a labelled
    reconstruction fallback and keep human review required.
    """
    queries=topic.get('visual_search_queries') or [f"{topic.get('title','')} {topic.get('era','')} historical artifact landscape"]
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    found, seen_pages, fingerprints, search_results = [], set(), [], []
    for query in queries[:6]:
        try:
            params={'action':'query','generator':'search','gsrsearch':f'filetype:bitmap {query}','gsrnamespace':6,'gsrlimit':12,
                    'prop':'imageinfo','iiprop':'url|extmetadata|mime|mediatype','iiurlwidth':1200,'format':'json'}
            response=session.get(API,params=params,headers={'User-Agent':'TurkTarihiDocumentary/0.6 (attribution and license review)'},timeout=(8,15))
            response.raise_for_status()
            pages=response.json().get('query',{}).get('pages',{})
            entries = [_metadata(page) for page in sorted(pages.values(), key=lambda page: page.get('index', 999))]
            search_results.append([(query, entry) for entry in entries if entry and entry['url']])
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            continue

    for row in zip_longest(*search_results):
        for option in row:
            if option is None:
                continue
            query, entry = option
            page = entry['description_url']
            if page in seen_pages:
                continue
            if len(seen_pages) >= 32:
                return found
            seen_pages.add(page)
            try:
                with session.get(entry['url'], headers={'User-Agent':'TurkTarihiDocumentary/0.6'},
                                 timeout=(8,15), stream=True) as response:
                    response.raise_for_status()
                    buffer = bytearray()
                    for chunk in response.iter_content(64 * 1024):
                        buffer.extend(chunk)
                        if len(buffer) > MAX_BYTES:
                            break
                if len(buffer) > MAX_BYTES:
                    continue
                with Image.open(BytesIO(buffer)) as image:
                    if min(image.size) < 480:
                        continue
                    image = ImageOps.exif_transpose(image).convert('RGB')
                fingerprint = _fingerprint(image)
                if any((fingerprint ^ previous).bit_count() <= 4 for previous in fingerprints):
                    continue
                portrait, framing = _portrait(image)
            except (requests.RequestException, OSError, ValueError, Image.DecompressionBombError):
                continue
            filename = output_dir / f'{len(found)+1:02d}_commons.jpg'
            portrait.save(filename, quality=92, optimize=True)
            entry.update({'file': filename.name, 'query': query, 'framing': framing,
                          'attribution': f"{entry['artist']} — {entry['license']}"})
            fingerprints.append(fingerprint)
            found.append(entry)
            if len(found) >= limit:
                return found
    return found


def write_attribution(items, path):
    path=Path(path)
    if not items:
        path.write_text('Bu taslakta lisanslı Commons görseli bulunamadı. Yerel çizimler açıkça temsili canlandırma olarak değerlendirilmelidir.\n',encoding='utf-8')
        return path
    lines=['# Görsel kaynakları ve atıflar','', 'Her dosyanın lisans ve kaynak sayfası kontrol edilmelidir.','']
    for index,item in enumerate(items,1):
        lines.extend([f"{index}. `{item['file']}` — **{item['title']}**",f"   - Arama/sahne bağlamı: {item.get('query','')}",f"   - Yazar/atıf: {item['attribution']}",f"   - Kaynak: {item['description_url']}",f"   - Lisans: {item['license_url'] or item['license']}"])
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return path
