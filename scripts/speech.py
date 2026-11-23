"""Offline Turkish narration via Piper. No paid service or API key."""
from pathlib import Path
import subprocess, sys, urllib.request, tempfile, wave

MODEL='tr_TR-dfki-medium'
BASE='https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/'

def ensure_model(cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    model=cache/(MODEL+'.onnx')
    cfg=cache/(MODEL+'.onnx.json')
    for f in (model,cfg):
        if not f.exists() or f.stat().st_size<500:
            with urllib.request.urlopen(BASE+f.name,timeout=100) as response, open(str(f)+'.part','wb') as target:
                while (part:=response.read(1024*1024)):target.write(part)
            Path(str(f)+'.part').replace(f)
    return model

def narrate(text,dest,cache):
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    model=ensure_model(cache)
    cmd=[sys.executable,'-m','piper','--model',str(model),'--output_file',str(dest),'--',text]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=160)
    if result.returncode or not dest.exists():raise RuntimeError('Piper TTS başarısız: '+result.stderr[-700:])
    if dest.stat().st_size<1000:raise RuntimeError('Piper çok küçük ses dosyası üretti')
    return dest

def narrate_segments(segments,dest,cache,recordings_dir=None):
    """Render short performance-led phrases separately, with controlled cadence.

    Piper is still a synthetic voice. Short phrase boundaries, rhetorical
    punctuation, modest pace changes and deliberate pauses give the edit more
    natural rhythm without claiming emotion controls the model does not have.
    Returns subtitle cues aligned to the actual rendered WAV durations.
    """
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    recordings_dir=Path(recordings_dir) if recordings_dir else None
    model=None if recordings_dir else ensure_model(cache)
    if not segments:raise ValueError('Seslendirme cümlesi yok')
    cues=[];parts=[];rate=None;channels=None;sampwidth=None;elapsed=0.0
    with tempfile.TemporaryDirectory(prefix='piper_performance_') as td:
        td=Path(td)
        for i,item in enumerate(segments):
            spoken=str(item['spoken']).strip()
            if not spoken:continue
            part=td/f'{i:02d}.wav'
            if recordings_dir:
                candidates=[recordings_dir/f'{i+1:02d}{ext}' for ext in ('.wav','.mp3','.m4a','.aac','.ogg')]
                source=next((f for f in candidates if f.is_file()),None)
                if source is None:raise ValueError(f'İnsan ses kaydı eksik: {i+1:02d}.wav (veya mp3/m4a/aac/ogg)')
                result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),
                    '-af','loudnorm=I=-18:TP=-2:LRA=11','-ar','22050','-ac','1','-c:a','pcm_s16le',str(part)],
                    capture_output=True,text=True,timeout=120)
                if result.returncode or not part.exists():raise RuntimeError(f'İnsan ses kaydı dönüştürülemedi ({source.name}): '+result.stderr[-500:])
            else:
                pace=float(item.get('pace',1.0))
                cmd=[sys.executable,'-m','piper','--model',str(model),'--output_file',str(part),
                     '--length-scale',str(pace),'--noise-scale',str(item.get('noise_scale',0.70)),
                     '--noise-w-scale',str(item.get('noise_w_scale',0.85)),'--',spoken]
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
                if result.returncode or not part.exists():raise RuntimeError('Piper TTS başarısız: '+result.stderr[-700:])
            with wave.open(str(part),'rb') as wf:
                current=(wf.getframerate(),wf.getnchannels(),wf.getsampwidth())
                if rate is None:rate,channels,sampwidth=current
                if current!=(rate,channels,sampwidth):raise RuntimeError('Piper ses parçalarının biçimi uyuşmuyor')
                frames=wf.readframes(wf.getnframes())
            duration=len(frames)/(rate*channels*sampwidth)
            start=elapsed;parts.append(frames);elapsed+=duration
            cues.append({'start':start,'end':elapsed,'text':str(item.get('caption',spoken))})
            pause=float(item.get('pause_after',0.22))
            if pause>0:
                silence_frames=int(rate*pause)
                parts.append(b'\0'*(silence_frames*channels*sampwidth));elapsed+=silence_frames/rate
        with wave.open(str(dest),'wb') as out:
            out.setframerate(rate);out.setnchannels(channels);out.setsampwidth(sampwidth)
            out.writeframes(b''.join(parts))
    if dest.stat().st_size<1000:raise RuntimeError('Piper çok küçük ses dosyası üretti')
    return cues
