"""Create an original low-volume instrumental ambience, with no external music licensing."""
from pathlib import Path
import numpy as np, wave

def create(seconds,path,rate=16000,*,maritime=False):
    n=int(rate*seconds);t=np.arange(n,dtype=np.float32)/rate
    base=np.zeros(n,dtype=np.float32)
    chords=((55,65.41,82.41),(43.65,55,65.41),(48.99,61.74,73.42),(41.2,51.91,61.74))
    for section, start in enumerate(np.arange(-2,seconds,8)):
        u=t-start
        fade=np.clip(u/2,0,1)*np.clip((10-u)/2,0,1)
        for f,gain in zip(chords[section%len(chords)],(.12,.08,.06)):
            base+=fade*gain*(np.sin(2*np.pi*f*t)+.15*np.sin(2*np.pi*(f*2+.15)*t))
    pulse=.09*np.sin(2*np.pi*110*t)*(np.maximum(np.sin(2*np.pi*.36*t),0)**3)
    drums=np.zeros(n,dtype=np.float32)
    for beat in np.arange(.7,seconds,3.2):
        i=int(beat*rate);length=min(int(.48*rate),n-i)
        if length<=0:break
        tt=np.arange(length,dtype=np.float32)/rate
        drums[i:i+length]+=.23*np.exp(-tt*15)*np.sin(2*np.pi*(60-35*tt)*tt)
    # Original foley synthesis: soft wind, slow surf swells, and a short paper texture.
    rng=np.random.default_rng(1513)
    noise=rng.normal(size=n).astype(np.float32)
    smooth=np.convolve(noise,np.hanning(81)/40,mode="same")
    air=.16*smooth*(.35+.65*np.sin(t*np.pi/5)**2)
    if maritime:
        surf=.27*smooth*(.12+.88*np.maximum(0,np.sin(t*np.pi/3.7))**2)
        paper=.023*(noise-smooth)*np.exp(-((t-.57)/.22)**2)
        air+=surf+paper
    envelope=np.minimum(1,t/.5)*np.maximum(0,np.minimum(1,(seconds-t)/2))
    audio=((base+pulse+drums+air)*envelope*.65).clip(-.95,.95)
    path=Path(path)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((audio*32767).astype('<i2').tobytes())
    return path
