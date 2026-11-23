"""Fetch Wikimedia Commons visuals only when an explicit free license is present."""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageOps
from io import BytesIO

API='https://commons.wikimedia.org/w/api.php'
MAX_BYTES=8_000_000


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


def fetch_visuals(topic, output_dir, session=requests, limit=10):
    """Search curated topic terms, save diverse licensed images and attribution.

    Returns an empty list on network/API problems; callers must use a labelled
    reconstruction fallback and keep human review required.
    """
    queries=topic.get('visual_search_queries') or [f"{topic.get('title','')} {topic.get('era','')} historical artifact landscape"]
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    found=[];seen=set()
    try:
        for query in queries:
            params={'action':'query','generator':'search','gsrsearch':f'filetype:bitmap {query}','gsrnamespace':6,'gsrlimit':12,
                    'prop':'imageinfo','iiprop':'url|extmetadata|mime|mediatype','iiurlwidth':1200,'format':'json'}
            response=session.get(API,params=params,headers={'User-Agent':'TurkTarihiDocumentary/0.6 (attribution and license review)'},timeout=(8,15))
            response.raise_for_status()
            pages=response.json().get('query',{}).get('pages',{})
            for page in pages.values():
                entry=_metadata(page)
                if not entry or not entry['url'] or entry['title'] in seen:continue
                image_response=session.get(entry['url'],headers={'User-Agent':'TurkTarihiDocumentary/0.6'},timeout=(8,15),stream=True)
                image_response.raise_for_status()
                chunks=[];size=0
                for chunk in image_response.iter_content(64*1024):
                    if not chunk:continue
                    size+=len(chunk)
                    if size>MAX_BYTES:break
                    chunks.append(chunk)
                if size>MAX_BYTES:continue
                try:
                    im=Image.open(BytesIO(b''.join(chunks))).convert('RGB')
                    if im.width<480 or im.height<480:continue
                    im=ImageOps.fit(im,(720,1280),method=Image.Resampling.LANCZOS)
                except Exception:
                    continue
                filename=output_dir/f'{len(found)+1:02d}_commons.jpg'
                im.save(filename,quality=92,optimize=True)
                entry.update({'file':filename.name,'query':query,'attribution':f"{entry['artist']} — {entry['license']}"})
                found.append(entry);seen.add(entry['title'])
                if len(found)>=limit:return found
    except Exception as exc:
        if found:
            return found
        return []
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
