"""Check minimum technical integrity of a finished narrated Reel.

This does not certify historical accuracy, copyright status, or artistic quality.
"""
from pathlib import Path
import argparse, subprocess, json, hashlib, re


def audio_levels(video):
    """Reject a technically present but practically silent/missing narration mix."""
    p=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','volumedetect','-vn','-f','null','-'],capture_output=True,text=True,check=True)
    text=p.stderr+'\n'+p.stdout
    mean=re.search(r'mean_volume:\s*(-?\d+(?:\.\d+)?) dB',text)
    peak=re.search(r'max_volume:\s*(-?\d+(?:\.\d+)?) dB',text)
    if not mean or not peak: raise ValueError('Ses miksaj seviyesi ölçülemedi')
    return float(mean.group(1)),float(peak.group(1))


def check(video,voiceover,subtitles,scenes):
    video=Path(video);voiceover=Path(voiceover);subtitles=Path(subtitles);scenes=Path(scenes)
    for f in (video,voiceover,subtitles):
        if not f.is_file() or f.stat().st_size<500: raise ValueError(f'Missing or suspiciously small production asset: {f}')
    if not scenes.is_dir(): raise ValueError('Visual scenes folder missing')
    images=[x for x in scenes.iterdir() if x.suffix.lower() in ('.png','.jpg','.jpeg','.webp')]
    if len(images)<10:raise ValueError('At least ten actual visual scene assets required')
    if len({hashlib.sha256(i.read_bytes()).hexdigest() for i in images})<10:raise ValueError('Visual scenes duplicate')
    p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],capture_output=True,text=True,check=True)
    info=json.loads(p.stdout)
    streams=info.get('streams',[])
    v=next((s for s in streams if s.get('codec_type')=='video'),None)
    a=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not v or not a:raise ValueError('A publishable Reel requires BOTH video and audio')
    mean_db,peak_db=audio_levels(video)
    if mean_db < -30 or peak_db < -15:
        raise ValueError(f'Seslendirme miksajı çok kısık veya eksik (ortalama {mean_db:.1f} dB, tepe {peak_db:.1f} dB)')
    w,h=v.get('width',0),v.get('height',0)
    if w<1080 or h<1920 or abs(w/h-9/16)>.012:raise ValueError('Video must be vertical >=1080x1920')
    duration=float(info.get('format',{}).get('duration',0))
    if duration<60 or duration>75:raise ValueError('Documentary Reel must be 60-75 seconds')
    if int(v.get('r_frame_rate','0/1').split('/')[0])<30:raise ValueError('Documentary Reel must be at least 30 fps')
    if subtitles.suffix.lower()!='.srt' or '-->' not in subtitles.read_text(encoding='utf-8'):raise ValueError('Valid SRT subtitles required')
    return {'technical_gate':'passed','manual_creative_and_historical_review':'still_required','duration_seconds':duration,'resolution':f'{w}x{h}','audio_mean_db':mean_db,'audio_peak_db':peak_db}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--video',required=True)
    p.add_argument('--voiceover',required=True)
    p.add_argument('--subtitles',required=True)
    p.add_argument('--scenes',required=True)
    args=p.parse_args()
    print(json.dumps(check(args.video,args.voiceover,args.subtitles,args.scenes),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
