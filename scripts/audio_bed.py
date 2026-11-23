"""Create an original low-volume instrumental ambience, with no external music licensing."""
from pathlib import Path
import numpy as np, wave

def create(seconds,path,rate=16000):
    n=int(rate*seconds);t=np.arange(n,dtype=np.float32)/rate
    # Layered minor chords, pulsing bass and original cinematic drums.
    base=(.22*np.sin(2*np.pi*55*t)+.13*np.sin(2*np.pi*65.41*t)+.09*np.sin(2*np.pi*82.41*t))
    pulse=.15*np.sin(2*np.pi*110*t)*(np.maximum(np.sin(2*np.pi*.36*t),0)**3)
    drums=np.zeros(n,dtype=np.float32)
    for beat in np.arange(0,seconds,2.4):
        i=int(beat*rate);length=min(int(.48*rate),n-i)
        if length<=0:break
        tt=np.arange(length,dtype=np.float32)/rate
        drums[i:i+length]+=.34*np.exp(-tt*13)*np.sin(2*np.pi*(60-35*tt)*tt)
    envelope=np.minimum(1,t/1.4)*np.minimum(1,(seconds-t)/1.6)
    audio=((base+pulse+drums)*envelope*.45).clip(-.95,.95)
    path=Path(path)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((audio*32767).astype('<i2').tobytes())
    return path
