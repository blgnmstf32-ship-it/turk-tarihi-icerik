"""Offline Turkish narration via Piper. No paid service or API key."""
from pathlib import Path
import json, subprocess, sys, urllib.request

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
