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

from PIL import Image

VALID_IMAGE_EXTS={'.png','.jpg','.jpeg','.webp'}


def ffprobe(path):
    r=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)


def media_duration(path):
    info=ffprobe(path)
    return float(info['format']['duration'])


def collect_scenes(folder):
    folder=Path(folder)
    if not folder.is_dir():raise ValueError(f'Sahne klasörü bulunamadı: {folder}')
    images=sorted(p for p in folder.iterdir() if p.suffix.lower() in VALID_IMAGE_EXTS)
    if len(images)<5:raise ValueError('En az 5 farklı sahne görseli gerekiyor')
    if len({hashlib.sha256(p.read_bytes()).hexdigest() for p in images})<5:
        raise ValueError('En az 5 gerçekten farklı görsel gerekiyor')
    for p in images:
        with Image.open(p) as im:
            im.verify()
    return images


def render_reel(scenes_dir,audio_path,srt_path,output_path,width=720,height=1280,fps=24):
    """Generate MP4 with slow documentary-style camera motion + narration + burnt-in SRT.

    This is video editing, not AI motion generation. Images should already carry
    strong visual storytelling and a suitable usage license.
    """
    scenes=collect_scenes(scenes_dir)
    audio=Path(audio_path).resolve();srt=Path(srt_path).resolve();out=Path(output_path).resolve()
    if not audio.is_file() or not srt.is_file(): raise ValueError('Seslendirme ve SRT altyazı dosyaları gereklidir')
    if '-->' not in srt.read_text(encoding='utf-8'):raise ValueError('Altyazı dosyası geçerli SRT değil')
    info=ffprobe(audio)
    if not any(s.get('codec_type')=='audio' for s in info['streams']):raise ValueError('Konuşma dosyası ses içermiyor')
    length=media_duration(audio)
    if not (20<=length<=60):raise ValueError('Seslendirme 20–60 saniye olmalı')
    out.parent.mkdir(parents=True,exist_ok=True)
    # Ensure each scene gets screen time with a gently changing frame.
    # Last scene receives any duration rounding remainder.
    per_scene=length/len(scenes)
    segments=[]
    with tempfile.TemporaryDirectory(prefix='turktarihi_reel_') as td:
        work=Path(td)
        for i,src in enumerate(scenes):
            path=work/f'scene_{i:03d}.mp4'; segments.append(path)
            dur=per_scene if i<len(scenes)-1 else length-per_scene*(len(scenes)-1)
            # Alternate gentle center-push and upward drift to avoid stationary slides.
            drift="x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'" if i%2==0 else "x='(iw-iw/zoom)/2':y='min((ih-ih/zoom),on/12)'"
            n=max(1,int(round(dur*fps)))
            vf=(f'scale={width}:{height}:force_original_aspect_ratio=increase,'
                f'crop={width}:{height},'
                f"zoompan=z='min(zoom+0.0009,1.16)':{drift}:d=1:s={width}x{height}:fps={fps},"
                f'format=yuv420p')
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(src),
                            '-vf',vf,'-frames:v',str(n),'-r',str(fps),'-c:v','libx264','-preset','ultrafast',
                            '-crf','24','-an',str(path)],check=True,capture_output=True,text=True)
        concat=work/'concat.txt'
        concat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.name}'\n" for p in segments),encoding='utf-8')
        # ASS/SRT subtitles burn-in with safe filename in temp work directory.
        srt_local=work/'captions.srt';srt_local.write_bytes(srt.read_bytes())
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y',
             '-f','concat','-safe','0','-i',str(concat),'-i',str(audio),
             '-vf',"subtitles=captions.srt:force_style='FontName=DejaVu Sans,FontSize=20,Outline=2,Shadow=1,MarginV=95'",
             '-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(out)]
        subprocess.run(cmd,cwd=work,check=True,capture_output=True,text=True)
    result=ffprobe(out)
    if not any(s.get('codec_type')=='audio' for s in result['streams']):raise RuntimeError('Çıktı ses içermiyor')
    return {'path':str(out),'seconds':round(media_duration(out),2),'scenes':len(scenes),
            'contains_audio_track':True,'speech_verified':False,'subtitle_burned_in':True,'instagram_published':False,
            'creative_review_required':True,'historical_review_required':True}


def main():
    ap=argparse.ArgumentParser(description='Ücretsiz FFmpeg ile anlatımlı tarih Reels montajı')
    ap.add_argument('--scenes',required=True,help='En az 5 farklı lisanslı PNG/JPG görsel içeren klasör')
    ap.add_argument('--voice',required=True,help='20–60 saniyelik seslendirme WAV/MP3')
    ap.add_argument('--subtitles',required=True,help='Senaryoyla eşleşen SRT altyazı')
    ap.add_argument('--out',required=True,help='Çıktı MP4 yolu')
    a=ap.parse_args()
    print(json.dumps(render_reel(a.scenes,a.voice,a.subtitles,a.out),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
