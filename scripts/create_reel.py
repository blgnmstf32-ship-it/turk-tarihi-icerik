"""Build an offline narrated Reel from ORIGINAL / licensed images and a narration WAV/MP3.

This program does NOT synthesize imagery or speech, claim source verification, or publish.
Its purpose is to automate the free editing stage once the real assets are ready.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import re
import shutil
import os

from PIL import Image

VALID_IMAGE_EXTS={'.png','.jpg','.jpeg','.webp'}


def ffprobe(path):
    r=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)


def media_duration(path):
    info=ffprobe(path)
    return float(info['format']['duration'])

def subtitle_cues(path):
    text=Path(path).read_text(encoding='utf-8')
    pattern=r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+([^\n]+)'
    def seconds(h,m,s,ms):return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
    return [{'start':seconds(*m.groups()[:4]),'end':seconds(*m.groups()[4:8]),'text':m.group(9).strip()}
            for m in re.finditer(pattern,text)]


def collect_scenes(folder):
    folder=Path(folder)
    if not folder.is_dir():raise ValueError(f'Sahne klasörü bulunamadı: {folder}')
    images=sorted(p for p in folder.iterdir() if p.suffix.lower() in VALID_IMAGE_EXTS)
    if len(images)<10:raise ValueError('Belgesel biçimi için en az 10 farklı sahne görseli gerekiyor')
    if len({hashlib.sha256(p.read_bytes()).hexdigest() for p in images})<10:
        raise ValueError('Belgesel biçimi için en az 10 gerçekten farklı görsel gerekiyor')
    for p in images:
        with Image.open(p) as im:
            im.verify()
    return images


def render_reel(scenes_dir,audio_path,srt_path,output_path,width=1080,height=1920,fps=30,three_scenes=None):
    """Render cinematic scene motion and active-word captions with Remotion."""
    scenes=collect_scenes(scenes_dir)
    audio=Path(audio_path).resolve();srt=Path(srt_path).resolve();out=Path(output_path).resolve()
    if not audio.is_file() or not srt.is_file(): raise ValueError('Seslendirme ve SRT altyazı dosyaları gereklidir')
    if '-->' not in srt.read_text(encoding='utf-8'):raise ValueError('Altyazı dosyası geçerli SRT değil')
    info=ffprobe(audio)
    if not any(s.get('codec_type')=='audio' for s in info['streams']):raise ValueError('Konuşma dosyası ses içermiyor')
    length=media_duration(audio)
    if not (60<=length<=75):raise ValueError('Belgesel seslendirmesi 60–75 saniye olmalı')
    if (width,height,fps)!=(1080,1920,30):raise ValueError('Varsayılan belgesel ölçüsü 1080x1920, 30 fps olmalı')
    out.parent.mkdir(parents=True,exist_ok=True)
    cues=subtitle_cues(srt)
    if not cues:raise ValueError('Zamanlı altyazı cümlesi bulunamadı')
    root=Path(__file__).resolve().parents[1]
    public_dir=root/'public'/'scenes'/out.stem
    public_dir.mkdir(parents=True,exist_ok=True)
    copied=[]
    for src in scenes:
        shutil.copy2(src,public_dir/src.name)
        copied.append({'src':f'scenes/{out.stem}/{src.name}'})
    three_scenes=three_scenes or []
    allowed={'battle_map','city_flyover','siege','artifact_gears'}
    for item in three_scenes:
        if item.get('kind') not in allowed:raise ValueError('Geçersiz 3D sahne türü')
        if item.get('from_sec',0)<0 or item.get('duration_sec',0)<=0:raise ValueError('3D sahne zamanlaması geçersiz')
        if item.get('from_sec',0)+item.get('duration_sec',0)>length:raise ValueError('3D sahne seslendirme süresinin dışına taşıyor')
    props={'durationSec':length,'title':'TARİHİN BİLİNMEYEN GERÇEKLERİ','scenes':copied,'captions':cues,
           'threeScenes':[{'kind':s['kind'],'title':s['title'],'labels':s.get('labels',[]),'fromSec':s['from_sec'],'durationSec':s['duration_sec']} for s in three_scenes]}
    with tempfile.TemporaryDirectory(prefix='turktarihi_remotion_') as td:
        props_path=Path(td)/'props.json'
        props_path.write_text(json.dumps(props,ensure_ascii=False),encoding='utf-8')
        cmd=['npx','--no-install','remotion','render','remotion/index.tsx','DocumentaryReel',str(out),
             '--props',str(props_path),'--codec=h264','--crf=22','--concurrency=2','--gl=angle','--log=error',
             '--license-key=free-license']
        try:
            env=os.environ.copy()
            compat=root/'scripts'/'remotion_node_compat.cjs'
            env['NODE_OPTIONS']=(env.get('NODE_OPTIONS','')+f' --require={compat}').strip()
            env['REMOTION_FORCE_LOOPBACK_NETWORK']='1'
            subprocess.run(cmd,cwd=root,env=env,check=True,capture_output=True,text=True,timeout=2400)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError('Remotion render başarısız: '+(exc.stderr or exc.stdout)[-1800:]) from exc
    result=ffprobe(out)
    if not any(s.get('codec_type')=='audio' for s in result['streams']):raise RuntimeError('Çıktı ses içermiyor')
    return {'path':str(out),'seconds':round(media_duration(out),2),'scenes':len(scenes),
            'renderer':'Remotion','fps':fps,'resolution':f'{width}x{height}',
            'contains_audio_track':False,'speech_verified':False,'animated_word_captions':True,'instagram_published':False,
            'creative_review_required':True,'historical_review_required':True,
            'three_d_scenes':len(three_scenes),'three_d_renderer':'Three.js via Remotion' if three_scenes else None}


def main():
    ap=argparse.ArgumentParser(description='Ücretsiz FFmpeg ile anlatımlı tarih Reels montajı')
    ap.add_argument('--scenes',required=True,help='En az 10 farklı tarihî görsel içeren klasör')
    ap.add_argument('--voice',required=True,help='60–75 saniyelik Türkçe belgesel anlatımı WAV/MP3')
    ap.add_argument('--subtitles',required=True,help='Senaryoyla eşleşen SRT altyazı')
    ap.add_argument('--out',required=True,help='Çıktı MP4 yolu')
    a=ap.parse_args()
    print(json.dumps(render_reel(a.scenes,a.voice,a.subtitles,a.out),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
